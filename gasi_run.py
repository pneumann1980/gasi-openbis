"""Record a measurement and optional released preparation on the Playground.

The DUT/resources must already have verified inventory identities. No types,
spaces, collections or duplicate sensor identities are created here. Later
analysis has its independent entry point in gasi_analysis.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile

import gasi_openbis_playground as ob
from gasi_local_measurements import NUMERIC_FIELDS, inspect_measurements

ROOT = Path(__file__).resolve().parent
RUN_PATH = ROOT / "config/gasi_run.json"
PHRASE = "UPLOAD CONFIGURED GASI RESEARCH WORKFLOW TO PLAYGROUND"
ACTIVITIES = ("preparation", "measurement", "analysis")
LABELS = {"preparation":"Vorbereitung", "measurement":"Beaufschlagung und Messung", "analysis":"Auswertung"}
HUMIDITY_UNITS = {"relative_humidity":"%RH", "dew_point":"degC", "frost_point":"degC", "water_amount_fraction":"umol/mol"}

def activities(run):
    if run.get("upload_scope","measurement")=="workflow":
        return ACTIVITIES
    mode=(run.get("preparation") or {}).get("mode","inline")
    return ("preparation","measurement") if mode=="create" else ("measurement",)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _finite(value):
    return isinstance(value, (float,int)) and not isinstance(value,bool) and math.isfinite(value)


def _reference(value):
    return isinstance(value,str) and bool(re.fullmatch(r"/[A-Z0-9_.-]+/(?:[A-Z0-9_.-]+/)?[A-Z0-9_.-]+",value))


def _time(value):
    # Python 3.10's fromisoformat does not yet accept the UTC suffix Z.
    return datetime.fromisoformat(value[:-1]+"+00:00" if isinstance(value,str) and value.endswith("Z") else value)


def _offset(value):
    if not isinstance(value,str) or not re.fullmatch(r"Z|[+-](?:0[0-9]|1[0-4]):[0-5][0-9]",value):
        return None
    return _time("2000-01-01T00:00:00"+value).tzinfo


def _record(value):
    return isinstance(value,int) and not isinstance(value,bool) and value>=1


def load_run(path=None):
    path = Path(path) if path is not None else RUN_PATH
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ob.CheckFailed("Die lokale Laufkonfiguration ist kein lesbares JSON.")
    if not isinstance(value,dict):
        raise ob.CheckFailed("Die lokale Laufkonfiguration muss ein JSON-Objekt sein.")
    return value


def load_measurement(path=None):
    value=load_run(path)
    if value is not None:
        value["upload_scope"]="measurement"
        value.setdefault("preparation",{"mode":"inline"})
    return value


def _source(root, value):
    if not isinstance(value,str) or not value:
        raise ob.CheckFailed("Expliziter Dateipfad fehlt.")
    path = (root / value).resolve()
    allowed = [root / "data/measurements", root / "data/results", root / "docs"]
    if not path.is_relative_to(root) or not path.is_file() or not any(path.is_relative_to(p.resolve()) for p in allowed):
        raise ob.CheckFailed("Uploaddateien müssen ausdrücklich unter data/measurements, data/results oder docs liegen.")
    if any(part.startswith(".") for part in path.relative_to(root).parts):
        raise ob.CheckFailed("Versteckte Dateien werden nicht in ein Uploadpaket aufgenommen.")
    if path.name.startswith(("GaSi_Konzeptmodell","GaSi_Datenmodell")):
        raise ob.CheckFailed("Allgemeine Modellgrafiken sind Projektdokumentation, kein tatsächlich verwendeter Laufplan.")
    return path


def validate_run(run, root=ROOT):
    """Collect missing scientific evidence without inventing a DUT or conditions."""
    root = Path(root).resolve()
    issues = []
    if not isinstance(run,dict):
        return ["Lokale Laufkonfiguration fehlt: config/gasi_run.example.json nach config/gasi_run.json kopieren."]
    if run.get("schema_version") != 1:
        issues.append("Laufschema muss Version 1 haben.")
    active=activities(run)
    later="analysis" in active
    for key in (("run_id","analysis_id","purpose","responsible_person") if later else ("run_id","purpose","responsible_person")):
        if not isinstance(run.get(key),str) or not run[key].strip():
            issues.append(f"Pflichtangabe fehlt: {key}.")
    for key in (("acquisition","analysis") if later else ("acquisition",)):
        if not str((run.get("software_versions") or {}).get(key) or "").strip():
            issues.append(f"Softwareversion fehlt: {key}.")
    dut = run.get("dut") or {}
    if not _reference(dut.get("identifier")) or dut.get("identity_confirmed") is not True:
        issues.append("Identität und vorhandene openBIS-ID des Sensor-Prüflings bestätigen.")
    if dut.get("kind") not in ("gas_sensor","gas_humidity_sensor"):
        issues.append("Prüflingsart: gas_sensor oder gas_humidity_sensor angeben.")
    for flag, evidence in (("setup_confirmed","setup_evidence"),("source_association_confirmed","source_association_evidence")):
        if run.get(flag) is not True or not str(run.get(evidence) or "").strip():
            issues.append(f"Bestätigung mit Beleg fehlt: {flag}.")
    assessment=run.get("reference_assessment") or {}
    if later and (assessment.get("confirmed") is not True or not assessment.get("basis") or not assessment.get("scope")):
        issues.append("Referenzgrundlage und Geltungsbereich der fachlichen Bewertung bestätigen.")
    resources = run.get("resources") or {}
    resource_refs={v for values in resources.values() if isinstance(values,list) for v in values if isinstance(v,str)}
    for evidence in run.get("reference_evidence",[]):
        if (not isinstance(evidence,dict) or evidence.get("resource_id") not in resource_refs or
            not evidence.get("document_reference") or not evidence.get("scope")):
            issues.append("Referenznachweis braucht verwendetes Gerät/Gascharge, Dokumentreferenz und Geltungsbereich.")
    for kind in ("instruments","gas_sources","sop","software"):
        values = resources.get(kind,[])
        if not isinstance(values,list) or (kind in ("instruments","gas_sources") and not values) or any(not _reference(v) for v in (values or [])):
            issues.append(f"Vorhandene Ressourcen-IDs prüfen: {kind}.")
        elif len(values) != len(set(values)):
            issues.append(f"Ressourcen-IDs sind mehrfach aufgeführt: {kind}.")
    times = run.get("times") or {}
    for activity in active:
        try:
            entry = times.get(activity) or {}
            start,end = [_time(entry[k]) for k in ("start","end")]
            if start.utcoffset() is None or end.utcoffset() is None or end < start:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            issues.append(f"{LABELS[activity]}: Beginn/Ende mit UTC-Offset und gültiger Reihenfolge fehlen.")
    stages = run.get("stages")
    if not isinstance(stages,list) or not stages:
        issues.append("Mindestens eine ausdrücklich beschriebene Messstufe fehlt.")
        stages = []
    ids = []
    for i,stage in enumerate(stages,1):
        if not isinstance(stage,dict):
            issues.append(f"Messstufe {i}: JSON-Objekt erforderlich.")
            continue
        ids.append(stage.get("stage_id"))
        if not isinstance(stage.get("stage_id"),str) or not stage["stage_id"].strip() or not _finite(stage.get("duration_s")) or stage["duration_s"] <= 0:
            issues.append(f"Messstufe {i}: Kennung und positive Dauer fehlen.")
        gas = stage.get("gas") or {}
        components = gas.get("components")
        if not gas.get("carrier") or gas.get("basis") not in ("dry","wet") or not isinstance(components,list) or not components:
            issues.append(f"Messstufe {i}: Trägergas, trocken/feucht-Bezug und nominelle Zusammensetzung fehlen.")
        else:
            for component in components:
                if not isinstance(component,dict) or not component.get("species") or not _finite(component.get("value")) or component["value"] < 0 or component.get("unit") not in ("mol/mol","umol/mol","nmol/mol","ppmV","%vol"):
                    issues.append(f"Messstufe {i}: Gaskomponente mit endlichem Gehalt und definierter Einheit erforderlich.")
                elif component["value"] > {"mol/mol":1,"umol/mol":1e6,"nmol/mol":1e9,"ppmV":1e6,"%vol":100}[component["unit"]]:
                    issues.append(f"Messstufe {i}: nomineller Gasgehalt überschreitet den physikalischen Anteil.")
        temperature = stage.get("temperature") or {}
        humidity = stage.get("humidity") or {}
        for title,entry,value_key in (("Temperatur",temperature,"setpoint_C"),("Feuchte",humidity,"value")):
            if not isinstance(entry.get("controlled"),bool) or not entry.get("location"):
                issues.append(f"Messstufe {i}: {title} benötigt Regelstatus und Mess-/Zielort.")
            elif entry["controlled"] is True and not _finite(entry.get(value_key)):
                issues.append(f"Messstufe {i}: endlicher {title}-Sollwert fehlt.")
            elif entry["controlled"] is False and (entry.get(value_key) is not None or not entry.get("uncontrolled_reason")):
                issues.append(f"Messstufe {i}: ungeregelte {title} mit Begründung, ohne erfundenen Sollwert dokumentieren.")
        if humidity.get("quantity") not in HUMIDITY_UNITS or humidity.get("unit") != HUMIDITY_UNITS.get(humidity.get("quantity")):
            issues.append(f"Messstufe {i}: Feuchtegröße und passende Einheit festlegen.")
        phase = humidity.get("saturation_phase")
        if (humidity.get("quantity")=="relative_humidity" and phase not in ("water","ice") or
            humidity.get("quantity")=="dew_point" and phase!="water" or
            humidity.get("quantity")=="frost_point" and phase!="ice"):
            issues.append(f"Messstufe {i}: Sättigungsbezug Wasser/Eis passend zur Feuchtegröße angeben.")
        if _finite(temperature.get("setpoint_C")) and temperature["setpoint_C"] <= -273.15:
            issues.append(f"Messstufe {i}: Temperatur ist physikalisch ungültig.")
        if humidity.get("quantity") == "relative_humidity":
            if not humidity.get("temperature_reference"):
                issues.append(f"Messstufe {i}: Temperaturbezug der relativen Feuchte fehlt.")
            if humidity.get("controlled") is True and _finite(humidity.get("value")) and not 0 <= humidity["value"] <= 100:
                issues.append(f"Messstufe {i}: relative Feuchte muss zwischen 0 und 100 %RH liegen.")
        pressure = stage.get("pressure") or {}
        if pressure.get("kind") != "absolute" or not _finite(pressure.get("value_Pa")) or pressure["value_Pa"] <= 0 or not pressure.get("location"):
            issues.append(f"Messstufe {i}: positiven absoluten Druck in Pa und Messort dokumentieren.")
    if len(ids) != len(set(str(v) for v in ids)):
        issues.append("Messstufenkennungen müssen eindeutig sein.")
    channels = run.get("channels")
    if not isinstance(channels,list):
        channels = []
    dut_channels = []
    seen_columns = set()
    resource_ids = {v for v in [dut.get("identifier")] if isinstance(v,str)} | {v for values in resources.values() if isinstance(values,list) for v in values if isinstance(v,str)}
    for channel in channels:
        if not isinstance(channel,dict) or channel.get("confirmed") is not True or not all(channel.get(k) for k in ("column","role","quantity","unit","location")) or not _reference(channel.get("object_identifier")) or channel.get("object_identifier") not in resource_ids:
            issues.append("Jeder ausgewertete Kanal benötigt bestätigte Objekt-, Größen-, Einheiten- und Messortzuordnung.")
            continue
        if channel["column"] in seen_columns:
            issues.append("Ein Kanal darf nicht mehrfach oder mit widersprüchlichen Rollen zugeordnet werden.")
        seen_columns.add(channel["column"])
        if channel["role"] == "dut_signal":
            dut_channels.append(channel)
            if channel["object_identifier"] != dut.get("identifier"):
                issues.append("Ein Prüflingssignal muss dem Sensor-Prüfling zugeordnet sein.")
        if channel["role"] == "reference_humidity" and (channel["quantity"] not in HUMIDITY_UNITS or channel["unit"] != HUMIDITY_UNITS.get(channel["quantity"])):
            issues.append("Feuchtereferenz benötigt eine konkrete Feuchtegröße und passende Einheit.")
        if channel["role"].startswith("reference_") and channel["object_identifier"]==dut.get("identifier"):
            issues.append("Der zu prüfende Sensor darf nicht seine eigene unabhängige Referenz sein.")
    if not dut_channels:
        issues.append("Mindestens ein bestätigter Sensorsignalkanal fehlt.")
    if later and dut.get("kind") == "gas_humidity_sensor" and not any(c.get("role") == "reference_humidity" for c in channels if isinstance(c,dict)):
        issues.append("Für die Feuchtebewertung den Referenzkanal und seine Größe dokumentieren.")
    for role in (("preparation","raw_data","analysis") if later else ("preparation","raw_data")):
        files = (run.get("files") or {}).get(role,[])
        if not isinstance(files,list) or (role != "preparation" and not files):
            issues.append(f"Explizite Dateien fehlen: {role}.")
            continue
        for value in files:
            try:
                _source(root,value)
            except ob.CheckFailed as exc:
                issues.append(f"{role}: {exc}")
    if set(run.get("files") or {}) - {"preparation","raw_data","analysis"}:
        issues.append("Dateien nur den Rollen preparation, raw_data oder analysis zuordnen.")
    raw_files = (run.get("files") or {}).get("raw_data",[])
    if not isinstance(raw_files,list):
        raw_files=[]
    selections = run.get("source_ranges")
    if not isinstance(selections,list):
        selections = []
    selected = [s.get("file") for s in selections if isinstance(s,dict)]
    if sorted(str(v) for v in selected) != sorted(str(v) for v in raw_files) or len(set(str(v) for v in selected)) != len(selected):
        issues.append("Für jede Loggerdatei genau einen ausdrücklich bestätigten Datenbereich source_ranges angeben.")
    for selection in selections:
        if (not isinstance(selection,dict) or selection.get("confirmed") is not True or
            any(not _record(selection.get(k)) for k in ("first_record","last_record")) or
            selection["last_record"] < selection["first_record"] or _offset(selection.get("utc_offset")) is None):
            issues.append("Datenbereiche benötigen bestätigte Record-Nummern und einen ausdrücklich bekannten utc_offset.")
    stage_ranges = run.get("stage_ranges")
    if not isinstance(stage_ranges,list):
        stage_ranges=[]
    mapped = set()
    for entry in stage_ranges:
        if not isinstance(entry,dict):
            issues.append("Stufenbereiche müssen JSON-Objekte sein.")
            continue
        mapped.add(str(entry.get("stage_id")))
        enclosing = next((s for s in selections if isinstance(s,dict) and s.get("file")==entry.get("file")),{})
        if (entry.get("confirmed") is not True or entry.get("stage_id") not in ids or
            not _record(entry.get("first_record")) or not _record(entry.get("last_record")) or
            not isinstance(enclosing.get("first_record"),int) or not isinstance(enclosing.get("last_record"),int) or
            not enclosing["first_record"] <= entry["first_record"] <= entry["last_record"] <= enclosing["last_record"]):
            issues.append("Jeder Stufenbereich muss bestätigt und vollständig innerhalb des gewählten Quelldatenbereichs liegen.")
    if mapped != set(str(v) for v in ids):
        issues.append("Jede aufgenommene Messstufe einem bestätigten Datenbereich stage_ranges zuordnen.")
    for i,entry in enumerate(stage_ranges):
        if not isinstance(entry,dict) or not _record(entry.get("first_record")) or not _record(entry.get("last_record")):
            continue
        for other in stage_ranges[i+1:]:
            if isinstance(other,dict) and other.get("file")==entry.get("file") and _record(other.get("first_record")) and _record(other.get("last_record")):
                if max(entry["first_record"],other["first_record"])<=min(entry["last_record"],other["last_record"]):
                    issues.append("Stufenbereiche derselben Loggerdatei dürfen sich nicht überschneiden.")
    if not later:
        preparation=run.get("preparation") or {"mode":"inline"}
        if preparation.get("mode") not in ("inline","create","reuse"):
            issues.append("Vorbereitung: inline, create oder reuse wählen.")
        if preparation.get("mode")=="create" and (not preparation.get("justification") or
            not (preparation.get("independently_released") is True or preparation.get("reused_across_runs") is True)):
            issues.append("Eigene Vorbereitung benötigt Freigabe-/Wiederverwendungsgrund, nicht nur plan.json.")
        if preparation.get("mode")=="reuse" and not _reference(preparation.get("identifier")):
            issues.append("Vorhandenen Vorbereitungsschritt ausdrücklich identifizieren.")
        policy=run.get("raw_file_policy") or {}
        if policy.get("mode")!="exclusive_run" or policy.get("confirmed") is not True or not policy.get("evidence"):
            issues.append("Pilot: eindeutige Dateizuordnung exclusive_run ausdrücklich bestätigen.")
        if policy.get("shared_sources"):
            issues.append("Gemeinsame Originaldateien: Vorschau möglich, Schreiben bis Live-Abnahme der gemeinsamen Ablage gesperrt.")
    return issues


def prepare_bundle(run, root=ROOT):
    """Copy only explicitly selected files; originals and local source evidence stay intact."""
    root = Path(root).resolve()
    issues = validate_run(run,root)
    if issues:
        raise ob.CheckFailed("Uploadpaket gesperrt: " + " ".join(issues))
    data = deepcopy(run)
    data.setdefault("upload_scope","measurement")
    data["resources"].setdefault("sop",[])
    data["resources"].setdefault("software",[])
    sources = []
    coverage={c["column"]:False for c in data["channels"]}
    paired_humidity=False
    active=activities(data)
    later="analysis" in active
    for role in (("preparation","raw_data","analysis") if later else ("preparation","raw_data")):
        values = data["files"].get(role,[])
        for index,value in enumerate(values):
            path = _source(root,value)
            content = path.read_bytes()
            if role == "raw_data":
                if path.suffix.lower() != ".csv":
                    raise ob.CheckFailed("Dieser GaSi-Importer erwartet validierbare Logger-CSV als RAW_DATA.")
                with tempfile.TemporaryDirectory(prefix="gasi-validate-") as temp:
                    folder = Path(temp)
                    (folder / path.name).write_bytes(content)
                    try:
                        checked = inspect_measurements(folder,folder / "preview.json")
                    except ValueError:
                        raise ob.CheckFailed("Logger-CSV besteht die lokale Zahlen-, Zeit- oder Zeilenprüfung nicht.") from None
                selection = next(s for s in data["source_ranges"] if s["file"]==value)
                if selection["last_record"] > checked["rows_checked"]:
                    raise ob.CheckFailed("Der gewählte Datenbereich überschreitet die geprüfte Loggerdatei.")
                import csv
                with io.StringIO(content.decode("utf-8-sig")) as stream:
                    reader=csv.DictReader(stream,delimiter="\t")
                    headers=tuple(reader.fieldnames)
                    if any(channel["column"] not in headers or channel["column"] not in NUMERIC_FIELDS for channel in data["channels"]):
                        raise ob.CheckFailed("Ein zugeordneter Zahlenkanal fehlt in einer ausgewählten Loggerdatei.")
                    number=0
                    previous=None
                    start=_time(data["times"]["measurement"]["start"])
                    end=_time(data["times"]["measurement"]["end"])
                    for row in reader:
                        if tuple(row.get(k) for k in headers)==headers:
                            continue
                        number+=1
                        if not selection["first_record"]<=number<=selection["last_record"]:
                            continue
                        stamp=datetime.strptime(row["Datum"]+" "+row["Uhrzeit"],"%d.%m.%Y %H:%M:%S").replace(tzinfo=_offset(selection["utc_offset"]))
                        if not start<=stamp<=end or previous is not None and stamp<previous:
                            raise ob.CheckFailed("Quelldaten passen nicht zu Laufzeit/UTC-Offset oder enthalten eine unaufgelöste Zeitrückstellung.")
                        previous=stamp
                        for column in coverage:
                            coverage[column]|=bool(row[column].strip())
                        has_dut=any(row[c["column"]].strip() for c in data["channels"] if c["role"]=="dut_signal")
                        has_reference=any(row[c["column"]].strip() for c in data["channels"] if c["role"]=="reference_humidity")
                        paired_humidity|=has_dut and has_reference
            sources.append({"activity":"measurement" if role=="raw_data" or role=="preparation" and "preparation" not in active else role,
                "type":"RAW_DATA" if role=="raw_data" else "ATTACHMENT",
                "slot":f"{role}_{index+1}", "filename":path.name,"sha256":_hash(content),"bytes":content})
    if not all(coverage.values()):
        raise ob.CheckFailed("Ein ausgewerteter Kanal enthält im bestätigten Datenbereich keine gültigen Messwerte.")
    if later and data["dut"]["kind"]=="gas_humidity_sensor" and not paired_humidity:
        raise ob.CheckFailed("Im Datenbereich fehlt eine gemeinsame Aufnahme von Sensorsignal und Feuchtereferenz.")
    key = "GASI_" + _hash(data["run_id"].encode("utf-8"))[:16].upper()
    # These two JSON datasets carry the scientific distinctions from the diagram.
    for activity,slot,payload in (
        ("preparation" if "preparation" in active else "measurement","plan",{"dut":data["dut"],"stages":data["stages"],"purpose":data["purpose"]}),
        ("measurement","context",{"dut":data["dut"],"resources":{k:v for k,v in data["resources"].items() if k!="software"},"channels":data["channels"],
            "reference_assessment":data.get("reference_assessment",{"confirmed":False}),
            "setup_evidence":data["setup_evidence"],"source_association_evidence":data["source_association_evidence"],
            "times":data["times"]["measurement"],"source_ranges":data["source_ranges"],"stage_ranges":data["stage_ranges"],
            "software_version":data["software_versions"]["acquisition"]}),
    ):
        content = _json(payload)
        sources.append({"activity":activity,"type":"ATTACHMENT","slot":slot,"filename":slot+".json",
                        "sha256":_hash(content),"bytes":content})
    content = _json({"analysis_id":data.get("analysis_id"),"software_version":data["software_versions"].get("analysis"),
        "input_object_code":key+"_MEASUREMENT","inputs":[
            {"dataset_name":key+"_"+e["slot"],"sha256":e["sha256"],"filename":e["filename"]}
            for e in sources if e["activity"]=="measurement"]})
    if later:
        sources.append({"activity":"analysis","type":"ATTACHMENT","slot":"analysis_context",
                        "filename":"analysis_context.json","sha256":_hash(content),"bytes":content})
    manifest = {"schema_version":1,"key":key,"run":data,
        "datasets":[{k:v for k,v in entry.items() if k!="bytes"} for entry in sources]}
    acquisition = deepcopy(data)
    acquisition.pop("analysis_id",None)
    acquisition["times"].pop("analysis",None)
    acquisition["resources"].pop("software",None)
    acquisition["software_versions"].pop("analysis",None)
    acquisition["files"].pop("analysis",None)
    acquisition_digest = _hash(_json({"run":acquisition,"datasets":[e for e in manifest["datasets"] if e["activity"]!="analysis"]}))
    manifest["acquisition_sha256"] = acquisition_digest
    manifest["activities"]=list(active)
    manifest["analysis_key"] = key + "_A" + _hash(str(data.get("analysis_id","")).encode("utf-8"))[:12].upper()
    manifest["analysis_sha256"] = _hash(_json({"acquisition_sha256":acquisition_digest,
        "analysis_id":data.get("analysis_id"),"times":data["times"].get("analysis"),
        "software_version":data["software_versions"].get("analysis"),"software_objects":data["resources"].get("software",[]),
        "datasets":[e for e in manifest["datasets"] if e["activity"]=="analysis"]}))
    digest = _hash(_json(manifest))
    # Keep paths usable in Windows workspaces and nested fresh-kernel test copies.
    output = root / ".local_playground_test/gasi_runs" / key / digest[:20]
    previous=output/"manifest.json"
    if previous.is_file() and _hash(previous.read_bytes())!=digest:
        raise ob.CheckFailed("Lokaler Paketpfad gehört zu einem anderen Manifest; Abbruch statt Überschreiben.")
    output.mkdir(parents=True,exist_ok=True)
    for entry in sources:
        folder = output / entry["slot"]
        folder.mkdir(exist_ok=True)
        (folder / entry["filename"]).write_bytes(entry["bytes"])
    (output / "manifest.json").write_bytes(_json(manifest))
    return {"path":output,"manifest":manifest,"sha256":digest}


def _targets(config, active=ACTIVITIES):
    settings = (config or {}).get("gasi_workflow") or {}
    scope = settings.get("approved_scope") or {}
    if settings.get("host") != ob.PLAYGROUND_HOST or scope.get("approved") is not True or not scope.get("reference"):
        raise ob.CheckFailed("Eigenständiges freigegebenes Playground-Ziel für den Forschungsablauf fehlt: gasi_workflow.")
    prefix = scope.get("lab_path_prefix")
    if not isinstance(prefix,str) or not re.fullmatch(r"/8[.]1[A-Z0-9_.-]*/[A-Z0-9_.-]+",prefix):
        raise ob.CheckFailed("Expliziten FB-8.1-Laborbuchprojekt-Präfix für den Forschungsablauf konfigurieren.")
    targets = settings.get("targets") or {}
    for activity in active:
        path = ob.target_path(targets.get(activity,{ }))
        if not path.startswith(prefix + "/"):
            raise ob.CheckFailed("Alle Forschungsziele müssen im ausdrücklich freigegebenen Laborbuchprojekt liegen.")
    return {key:targets[key] for key in active}


def preflight(client, bundle, config):
    """Read host, identities, schemas, vocabularies and every target again."""
    if str(client.url).rstrip("/") != ob.PLAYGROUND_HOST:
        raise ob.CheckFailed("Forschungsupload ist ausschließlich auf dem BAM-Playground erlaubt.")
    active=bundle["manifest"].get("activities",ACTIVITIES)
    targets = _targets(config,active)
    report = ob.discover_playground(client,config)
    for activity,target in targets.items():
        if activity in ACTIVITIES and ob.identifier(client.get_experiment(ob.target_path(target))) != ob.target_path(target):
            raise ob.CheckFailed("Laborbuch-Collection nicht eindeutig lesbar.")
    run = bundle["manifest"]["run"]
    refs = {run["dut"]["identifier"]} | {v for key,values in run["resources"].items() if key!="software" or "analysis" in active for v in values}
    preparation=run.get("preparation") or {}
    if preparation.get("mode")=="reuse":
        refs.add(preparation["identifier"])
    for reference in sorted(refs):
        obj = client.get_sample(reference)
        if ob.identifier(obj) != reference or not ob.code(ob.field(obj,"type")):
            raise ob.CheckFailed("Prüfling oder Ressource nicht eindeutig lesbar.")
        type_code = ob.code(ob.field(obj,"type"))
        if reference == run["dut"]["identifier"] and not any(type_code == t or type_code.startswith(t+".") for t in ("INSTRUMENT","SAMPLE","TEST_OBJECT")):
            raise ob.CheckFailed("Das konfigurierte Prüfobjekt hat keinen bestätigten Sensor-/Prüflingstyp.")
        if reference in run["resources"]["instruments"] and not (type_code=="INSTRUMENT" or type_code.startswith("INSTRUMENT.")):
            raise ob.CheckFailed("Ein konfiguriertes Gerät ist kein INSTRUMENT.")
        if reference in run["resources"]["gas_sources"] and type_code not in ("GAS_BOTTLE","CHEMICAL"):
            raise ob.CheckFailed("Eine konfigurierte Gasquelle ist kein bestätigtes Gas-/Materialobjekt.")
        if reference in run["resources"]["sop"] and type_code not in ("SOP","DOCUMENT"):
            raise ob.CheckFailed("Die konfigurierte SOP hat keinen bestätigten Verfahrenstyp.")
        if reference in run["resources"].get("software",[]) and type_code not in ("SOFTWARE_CODE","JUPYTER_NOTEBOOK"):
            raise ob.CheckFailed("Die konfigurierte Auswertesoftware hat keinen bestätigten Softwaretyp.")
        if reference==preparation.get("identifier") and type_code!="EXPERIMENTAL_STEP":
            raise ob.CheckFailed("Vorbereitungsreferenz ist kein EXPERIMENTAL_STEP.")
    for t in ("EXPERIMENTAL_STEP",):
        if not report["object_types"].get(t,{}).get("schema_confirmed"):
            raise ob.CheckFailed("EXPERIMENTAL_STEP-Schema nicht bestätigt.")
    for t in ("RAW_DATA","ATTACHMENT"):
        if not report["dataset_types"].get(t,{}).get("schema_confirmed"):
            raise ob.CheckFailed(f"{t}-Schema nicht bestätigt.")
    planned = {}
    for activity in active:
        suffix = f" – {run['analysis_id']}" if activity=="analysis" else ""
        values = {"$NAME":f"GaSi {run['run_id']} – {LABELS[activity]}{suffix}",
            "START_DATE":run["times"][activity]["start"],"END_DATE":run["times"][activity]["end"],
            "NOTES":_json({"gasi_workflow":1,"key":bundle["manifest"]["key"],"activity":activity,
                          "content_sha256":bundle["manifest"]["analysis_sha256" if activity=="analysis" else "acquisition_sha256"],"purpose":run["purpose"],
                          "responsible_person":run["responsible_person"]}).decode("utf-8")}
        planned[activity] = ob.mapped_properties(values,report["object_types"]["EXPERIMENTAL_STEP"],report)
        assigned={a["code"] for a in report["object_types"]["EXPERIMENTAL_STEP"]["assignments"]}
        for key,value in (("REFERENCE",run["run_id"]),("EXPERIMENTAL_STEP.EXPERIMENTAL_GOALS",run["purpose"])):
            if key in assigned:
                planned[activity][key]=value
    dataset_props = {}
    for entry in bundle["manifest"]["datasets"]:
        owner_key = bundle["manifest"]["analysis_key"] if entry["activity"]=="analysis" else bundle["manifest"]["key"]
        stable_name=("GASI_RAW_"+entry["sha256"] if run.get("upload_scope")=="measurement" and entry["type"]=="RAW_DATA"
                     else owner_key+"_"+entry["slot"])
        values = {"$NAME":stable_name,"NOTES":_json({"sha256":entry["sha256"]}).decode("utf-8")}
        dataset_props[entry["slot"]] = ob.mapped_properties(values,report["dataset_types"][entry["type"]],report)
    return targets, planned, dataset_props


def ensure_workflow(client, bundle, config):
    """Idempotent activity graph; every dataset is downloaded and hash checked."""
    # Validate immutable local package before any writes, including on resumption.
    if _hash(_json(bundle["manifest"])) != bundle["sha256"]:
        raise ob.CheckFailed("Uploadmanifest wurde nach der Vorbereitung verändert.")
    for entry in bundle["manifest"]["datasets"]:
        path = bundle["path"] / entry["slot"] / entry["filename"]
        if _hash(path.read_bytes()) != entry["sha256"]:
            raise ob.CheckFailed("Datei im Uploadpaket wurde nach der Vorbereitung verändert.")
    targets, properties, dataset_props = preflight(client,bundle,config)
    gateway = ob.PybisGateway(client)
    run = bundle["manifest"]["run"]
    existing = {}
    active=bundle["manifest"].get("activities",ACTIVITIES)
    for activity in active:
        object_code = (bundle["manifest"]["analysis_key"] if activity=="analysis" else bundle["manifest"]["key"]+"_"+activity.upper())
        obj = gateway.find_object(targets[activity],"EXPERIMENTAL_STEP",object_code)
        if obj and not _object_matches(obj,properties[activity]):
            raise ob.CheckFailed("Laufkennung existiert mit anderer Konfiguration; neue fachliche Laufkennung verwenden.")
        existing[activity] = obj
        if obj:
            for entry in bundle["manifest"]["datasets"]:
                if entry["activity"] == activity:
                    dataset = gateway.find_dataset(obj,entry["type"],dataset_props[entry["slot"]]["$NAME"])
                    if dataset:
                        _dataset_target(dataset,targets[activity])
                        gateway.verify_dataset_hash(dataset,entry["sha256"],entry["filename"])
    for activity,obj in existing.items():
        if not obj:
            continue
        expected = set(run["resources"]["sop"] if activity=="preparation" else
            [run["dut"]["identifier"],*run["resources"]["instruments"],*run["resources"]["gas_sources"]]
            if activity=="measurement" else run["resources"]["software"])
        if activity=="measurement" and "preparation" not in active and run.get("preparation",{}).get("mode","inline")=="inline":
            expected.update(run["resources"].get("sop",[]))
        predecessor = "preparation" if activity=="measurement" and "preparation" in active else "measurement" if activity=="analysis" else None
        if predecessor:
            if not existing.get(predecessor):
                raise ob.CheckFailed("Vorhandener Folgeschritt ohne Vorgänger; Teilstand manuell prüfen.")
            expected.add(ob.identifier(existing[predecessor]))
        if gateway.object_parents(obj)-expected:
            allowed={run.get("preparation",{}).get("identifier")} if activity=="measurement" else set()
            if gateway.object_parents(obj)-expected-allowed:
                raise ob.CheckFailed("Vorhandener Schritt hat zusätzliche, nicht konfigurierte Parents; manuell prüfen.")
    objects, results = {}, {"objects":{},"datasets":[]}
    if run.get("upload_scope")=="measurement":
        raw_hashes=[e["sha256"] for e in bundle["manifest"]["datasets"] if e["type"]=="RAW_DATA"]
        if len(raw_hashes)!=len(set(raw_hashes)):
            raise ob.CheckFailed("Identische Originaldatei mehrfach ausgewählt; Quelle einmalig zuordnen.")
        _check_raw_ownership(client,bundle,existing.get("measurement"))
    for activity in active:
        parents = []
        if activity == "preparation":
            parents = run["resources"]["sop"]
        elif activity == "measurement":
            parents = [run["dut"]["identifier"],*run["resources"]["instruments"],*run["resources"]["gas_sources"]]
            if "preparation" in objects:
                parents.append(ob.identifier(objects["preparation"]))
            elif run.get("preparation",{}).get("mode")=="reuse":
                parents.append(run["preparation"]["identifier"])
            else:
                parents.extend(run["resources"].get("sop",[]))
        else:
            parents = [ob.identifier(objects["measurement"]),*run["resources"]["software"]]
        obj = existing[activity]
        created = obj is None
        code = (bundle["manifest"]["analysis_key"] if activity=="analysis" else bundle["manifest"]["key"]+"_"+activity.upper())
        if obj is None:
            obj = gateway.create_object(targets[activity],"EXPERIMENTAL_STEP",code,properties[activity],parents=sorted(set(parents)))
        for reference in sorted(set(parents)-gateway.object_parents(obj)):
            gateway.add_parent(obj,reference)
        obj = gateway.find_object(targets[activity],"EXPERIMENTAL_STEP",code)
        if obj is None or set(parents)!=gateway.object_parents(obj) or not _object_matches(obj,properties[activity]):
            raise ob.CheckFailed("Objektbeziehungen nach Speichern nicht bestätigt.")
        objects[activity] = obj
        results["objects"][activity] = {"identifier":ob.identifier(obj),"collection":ob.target_path(targets[activity]),
                                      "created":created,**ob.browser_reference(obj,"object")}
        for entry in bundle["manifest"]["datasets"]:
            if entry["activity"] != activity:
                continue
            values = dataset_props[entry["slot"]]
            dataset = gateway.find_dataset(obj,entry["type"],values["$NAME"])
            created = dataset is None
            if dataset is None:
                gateway.create_dataset(targets[activity],obj,entry["type"],values,bundle["path"]/entry["slot"]/entry["filename"])
                dataset = gateway.find_dataset(obj,entry["type"],values["$NAME"])
            if dataset is None:
                raise ob.CheckFailed("Dataset nach Speichern nicht lesbar; mit gleicher Kennung erneut prüfen.")
            _dataset_target(dataset,targets[activity])
            digest = gateway.verify_dataset_hash(dataset,entry["sha256"],entry["filename"])
            results["datasets"].append({"activity":activity,"identifier":ob.identifier(dataset),
                "sha256":digest,"filename":entry["filename"],"slot":entry["slot"],
                "created":created,**ob.browser_reference(dataset,"dataset")})
    results["dut"] = {"identifier":run["dut"]["identifier"],"reused":True}
    if run.get("upload_scope")=="measurement":
        _save_source_receipt(client,gateway,bundle,targets["measurement"],objects["measurement"],results)
    return results


def dataset_file(dataset, filename):
    """Resolve the actual server-side relative path, never assume basename layout."""
    paths=list(dataset.file_list)
    matches=[str(p).lstrip("/") for p in paths if Path(str(p)).name==filename]
    if len(matches)!=1 or ".." in Path(matches[0]).parts:
        raise ob.CheckFailed("Dateipfad im Dataset nicht eindeutig.")
    return matches[0]


def _check_raw_ownership(client,bundle,measurement):
    hashes={e["sha256"] for e in bundle["manifest"]["datasets"] if e["type"]=="RAW_DATA"}
    for row in ob.table_records(client.get_datasets(type="RAW_DATA",props=["$NAME","NOTES"])):
        note=next((v for k,v in {**ob.props(row),**row}.items() if ob.propkey(k)=="notes"),"")
        try: digest=json.loads(note).get("sha256")
        except (ValueError,TypeError,AttributeError): digest=None
        if digest not in hashes and ob.name(row) not in {"GASI_RAW_"+h for h in hashes}:
            continue
        dataset=client.get_dataset(ob.identifier(row))
        owner=ob.field(ob.field(dataset,"attrs",dataset),"sample")
        owner=owner if isinstance(owner,str) else ob.identifier(owner)
        if measurement is None or owner!=ob.identifier(measurement):
            raise ob.CheckFailed("Originaldatei ist bereits einem anderen erfassenden Objekt zugeordnet. Gemeinsame Ablage ist gesperrt.")


def _save_source_receipt(client,gateway,bundle,target,measurement,results):
    run=bundle["manifest"]["run"]
    inputs=[]
    for entry in bundle["manifest"]["datasets"]:
        if entry["type"]!="RAW_DATA":continue
        saved=next(r for r in results["datasets"] if r["slot"]==entry["slot"])
        dataset=client.get_dataset(saved["identifier"])
        source=run["files"]["raw_data"][int(entry["slot"].rsplit("_",1)[1])-1]
        inputs.append({"measurement_id":ob.identifier(measurement),"dataset_id":ob.identifier(dataset),
            "dataset_code":ob.field(dataset,"code"),"file_path":dataset_file(dataset,entry["filename"]),
            "sha256":entry["sha256"],"source_ranges":[v for v in run["source_ranges"] if v["file"]==source],
            "stage_ranges":[v for v in run["stage_ranges"] if v["file"]==source]})
    receipt={"schema_version":2,"run_id":run["run_id"],"inputs":inputs,"times":run["times"]["measurement"],
        "reference_assessment":run.get("reference_assessment"),"reference_evidence":run.get("reference_evidence",[]),
        "resources":run["resources"],"channels":run["channels"],"stages":run["stages"]}
    content=_json(receipt);digest=_hash(content)
    path=bundle["path"]/"source_receipt.json";path.write_bytes(content)
    stable=bundle["manifest"]["key"]+"_SOURCE_RECEIPT"
    dataset=gateway.find_dataset(measurement,"ATTACHMENT",stable)
    if dataset is None:
        gateway.create_dataset(target,measurement,"ATTACHMENT",{"$NAME":stable},path)
        dataset=gateway.find_dataset(measurement,"ATTACHMENT",stable)
    if dataset is None:raise ob.CheckFailed("Quellmanifest nicht zurücklesbar.")
    gateway.verify_dataset_hash(dataset,digest,path.name)
    results["source_receipt"]={"dataset_id":ob.identifier(dataset),"sha256":digest,"inputs":inputs,
                             **ob.browser_reference(dataset,"dataset")}


def _notes(obj):
    return next((v for k,v in ob.props(obj).items() if ob.propkey(k)=="notes"),None)


def _object_matches(obj,expected):
    if ob.name(obj)!=expected["$NAME"] or _notes(obj)!=expected["NOTES"]:
        return False
    actual={ob.propkey(k):v for k,v in ob.props(obj).items()}
    try:
        return all(_time(str(actual[key.lower()]))==_time(expected[key])
                   for key in ("START_DATE","END_DATE"))
    except (KeyError,ValueError,TypeError):
        return False


def _dataset_target(dataset,target):
    collection=ob.field(ob.field(dataset,"attrs",dataset),"experiment")
    path=collection if isinstance(collection,str) else ob.identifier(collection)
    if path!=ob.target_path(target):
        raise ob.CheckFailed("Dataset liegt nicht in der konfigurierten Laborbuch-Collection.")


def upload_workflow(*, enabled=False, confirmation="", expected_manifest_sha=None, root=ROOT):
    """Notebook boundary: defaults do nothing; never print a token or a raw server error."""
    if not enabled or confirmation != PHRASE:
        return None,"Vorschau: kein Upload. Schreibzelle bleibt deaktiviert."
    if not isinstance(expected_manifest_sha,str) or not re.fullmatch(r"[0-9a-f]{64}",expected_manifest_sha):
        return None,"Upload gesperrt: zuerst die vollständige lokale Vorschau erzeugen."
    try:
        root = Path(root).resolve()
        run = load_measurement(root / "config/gasi_run.json")
        bundle = prepare_bundle(run,root)
        if bundle["sha256"]!=expected_manifest_sha:
            raise ob.CheckFailed("Laufdaten haben sich seit der Vorschau geändert. Vorschau erneut prüfen.")
        config,message = ob.load_target_config(root / "config/playground_test_target.json")
        if config is None:
            return None,message
        _targets(config,bundle["manifest"]["activities"])
        client,message = ob.connect_playground()
        if client is None:
            return None,message
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            result = ensure_workflow(client,bundle,config)
        (bundle["path"] / "verification.json").write_bytes(_json(result))
        return result,"Messung, Parents, Quellmanifest und alle Original-Hashes nach Rückdownload bestätigt."
    except ob.CheckFailed as exc:
        return None,str(exc)
    except Exception:
        return None,"Upload unterbrochen. Teilstand kann gespeichert sein; unveränderte Laufkennung erneut verwenden. Serverdetails werden nicht ausgegeben."
