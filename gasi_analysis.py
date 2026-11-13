"""Later analysis of one or more recorded measurements, with exact server provenance."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path, PurePosixPath
import re
import tempfile

import gasi_openbis_playground as ob
import gasi_run as runs

ROOT=runs.ROOT


def validate_analysis(config,root=ROOT):
    issues=[]
    if not isinstance(config,dict):return ["config/gasi_analysis.json fehlt; leere Vorlage kopieren."]
    for key in ("analysis_id","purpose","responsible_person","software_version","selection_rules"):
        if not isinstance(config.get(key),str) or not config[key].strip():issues.append(f"Auswertung: {key} fehlt.")
    try:
        start,end=[runs._time(config["times"][k]) for k in ("start","end")]
        if start.utcoffset() is None or end.utcoffset() is None or end<start:raise ValueError
        if start.microsecond or end.microsecond:issues.append("openBIS-Auswertungszeiten benötigen ganze Sekunden; keine Rundung.")
    except (KeyError,TypeError,ValueError):issues.append("Auswertungszeiten mit UTC-Offset fehlen.")
    if not isinstance(config.get("parameters"),dict):issues.append("Auswerteparameter als JSON-Objekt dokumentieren.")
    assessment=config.get("reference_assessment") or {}
    if assessment.get("confirmed") is not True or not assessment.get("basis") or not assessment.get("scope"):
        issues.append("Referenzbewertung mit Grundlage und Geltungsbereich fehlt.")
    evidence=config.get("reference_evidence") or []
    for item in evidence:
        if not all(item.get(k) for k in ("resource_id","document_reference","scope")) or not runs._reference(item["resource_id"]):
            issues.append("Kalibrier-/Zertifikatsbezug braucht Ressourcen-ID, Nachweis und Geltungsbereich.")
    kind=config.get("purpose_kind")
    if kind not in ("characterization","calibration","conformity"):issues.append("Prüfzweck als characterization/calibration/conformity festlegen.")
    if kind in ("calibration","conformity") and (not evidence or not config.get("uncertainty") or not config.get("stable_windows")):
        issues.append("Kalibrierung/Anforderungsprüfung braucht Nachweise, stabile Fenster und Messunsicherheit.")
    if kind in ("calibration","conformity") and any(not e.get("conditions") for e in evidence):
        issues.append("Kalibrier-/Zertifikatsnachweise brauchen ihre gültigen Bezugsbedingungen.")
    if kind=="conformity" and (not config.get("requirements") or not config.get("decision_rule")):
        issues.append("Anforderungsprüfung braucht Grenzwerte mit Einheiten und Entscheidungsregel.")
    if kind=="conformity":
        for rule in config.get("requirements",[]):
            if not isinstance(rule,dict) or not rule.get("quantity") or not rule.get("unit") or not any(runs._finite(rule.get(k)) for k in ("lower_limit","upper_limit")):
                issues.append("Jeder Grenzwert braucht Größe, Einheit und numerische untere/obere Grenze.")
    inputs=config.get("inputs") or []
    if not inputs:issues.append("Mindestens ein tatsächlich verwendetes Eingabedataset fehlt.")
    seen=set()
    for item in inputs:
        if not runs._reference(item.get("measurement_id")) or not item.get("dataset_id") or not item.get("file_path"):
            issues.append("Eingabe braucht Messlauf-ID, Dataset-ID und relativen Dateipfad.")
        path=PurePosixPath(str(item.get("file_path","")))
        if path.is_absolute() or ".." in path.parts or not path.parts:issues.append("Dataset-Dateipfad muss sicher und relativ sein.")
        if not re.fullmatch(r"[a-f0-9]{64}",str(item.get("sha256",""))):issues.append("Original-SHA-256 fehlt.")
        key=(item.get("dataset_id"),item.get("file_path"))
        if key in seen:issues.append("Eine Eingabedatei nur einmal aufführen; mehrere Bereiche in ranges angeben.")
        seen.add(key)
        for label in ("source_ranges","stage_ranges"):
            if not isinstance(item.get(label), list) or label == "source_ranges" and not item[label]:issues.append(f"Auswahl {label} fehlt.")
            for area in item.get(label,[]):
                if not runs._record(area.get("first_record")) or not runs._record(area.get("last_record")) or area["last_record"]<area["first_record"]:
                    issues.append("Ungültiger Record-Bereich in der Auswertung.")
        for area in item.get("source_ranges",[]):
            if runs._offset(area.get("utc_offset")) is None:issues.append("UTC-Offset der ausgewerteten Eingabe fehlt.")
    files=config.get("files") or []
    if not files:issues.append("Ergebnisdateien fehlen.")
    for name in files:
        try:runs._source(Path(root).resolve(),name)
        except ob.CheckFailed as exc:issues.append(str(exc))
    for reference in config.get("software_objects",[]):
        if not runs._reference(reference):issues.append("Softwareobjekt-ID ungültig.")
    return issues


def prepare_analysis(config,root=ROOT):
    root=Path(root).resolve()
    issues=validate_analysis(config,root)
    if issues:raise ob.CheckFailed("Auswertung gesperrt: "+" ".join(issues))
    entries=[]
    for index,name in enumerate(config["files"]):
        source=runs._source(root,name);content=source.read_bytes()
        entries.append({"slot":f"result_{index+1}","filename":source.name,"sha256":runs._hash(content),"bytes":content})
    metadata={"config":deepcopy(config),"results":[{k:v for k,v in e.items() if k!="bytes"} for e in entries]}
    digest=runs._hash(runs._json(metadata))
    path=root/".local_playground_test/analyses"/digest[:20]
    path.mkdir(parents=True,exist_ok=True)
    for entry in entries:
        folder=path/entry["slot"];folder.mkdir(exist_ok=True)
        (folder/entry["filename"]).write_bytes(entry.pop("bytes"))
    return {"path":path,"config":deepcopy(config),"entries":entries,"sha256":digest}


def download_bytes(dataset,file_path):
    if file_path not in [str(p).lstrip("/") for p in dataset.file_list]:
        raise ob.CheckFailed("Datei ist nicht im angegebenen Serverdataset vorhanden.")
    with tempfile.TemporaryDirectory(prefix="gasi-input-") as temp:
        # Preserve directories to distinguish identically named files.
        dataset.download(destination=temp,create_default_folders=False)
        found=[p for p in Path(temp).rglob("*") if p.is_file() and
               (p.relative_to(temp).as_posix()==file_path or p.as_posix().endswith("/"+file_path))]
        if not found and sum(PurePosixPath(str(p)).name==PurePosixPath(file_path).name for p in dataset.file_list)==1:
            # pyBIS may flatten a single-file download with this option.
            found=list(Path(temp).rglob(PurePosixPath(file_path).name))
        if len(found)!=1:raise ob.CheckFailed("Rückdownload lässt den relativen Dateipfad nicht eindeutig auflösen.")
        return found[0].read_bytes()


def _receipt(client,measurement):
    matches=[]
    for item in ob.records(measurement.get_datasets()):
        dataset=client.get_dataset(ob.identifier(item))
        if any(PurePosixPath(str(p)).name=="source_receipt.json" for p in dataset.file_list):
            matches.append(dataset)
    if len(matches)!=1:raise ob.CheckFailed("Eindeutiges serverseitiges Quellmanifest der Messung fehlt.")
    dataset=matches[0];path=runs.dataset_file(dataset,"source_receipt.json")
    content=download_bytes(dataset,path)
    value=json.loads(content)
    value["_server_source"]={"dataset_id":ob.identifier(dataset),"dataset_code":ob.field(dataset,"code"),
                             "file_path":path,"sha256":runs._hash(content)}
    return value


def _subset(selected,recorded, *,stage=False):
    for area in selected:
        if not any(v["first_record"]<=area["first_record"]<=area["last_record"]<=v["last_record"] and
                   (not area.get("file") or not v.get("file") or area["file"]==v["file"]) and
                   (area.get("stage_id")==v.get("stage_id") if stage else area.get("utc_offset")==v.get("utc_offset"))
                   for v in recorded):
            raise ob.CheckFailed("Auswertebereich oder Zeit-/Stufenbezug liegt außerhalb des registrierten Messbereichs.")


def resolve_inputs(client,config):
    resolved=[];cache={}
    for item in config["inputs"]:
        measurement=client.get_sample(item["measurement_id"])
        if ob.identifier(measurement)!=item["measurement_id"] or ob.code(ob.field(measurement,"type"))!="EXPERIMENTAL_STEP":
            raise ob.CheckFailed("Eingabe ist kein eindeutig identifizierter Messlauf.")
        if item["measurement_id"] not in cache:cache[item["measurement_id"]]=_receipt(client,measurement)
        receipt=cache[item["measurement_id"]]
        dataset=client.get_dataset(item["dataset_id"])
        if ob.code(ob.field(dataset,"type"))!="RAW_DATA":raise ob.CheckFailed("Eingabe muss RAW_DATA sein.")
        actual_id=ob.identifier(dataset)
        owner=ob.field(ob.field(dataset,"attrs",dataset),"sample")
        owner=owner if isinstance(owner,str) else ob.identifier(owner)
        if owner!=item["measurement_id"]:raise ob.CheckFailed("RAW_DATA gehört nicht zum angegebenen erfassenden Messlauf.")
        original=next((v for v in receipt["inputs"] if v["dataset_id"]==actual_id and v["file_path"]==item["file_path"]),None)
        if original is None:raise ob.CheckFailed("Dataset/Dateipfad fehlen im zurückgelesenen Quellmanifest.")
        raw=download_bytes(dataset,item["file_path"])
        digest=runs._hash(raw)
        if digest!=item["sha256"] or digest!=original["sha256"]:raise ob.CheckFailed("Eingabe-Hash stimmt nicht mit Original und Messmanifest überein.")
        _subset(item["source_ranges"],original["source_ranges"])
        if original["stage_ranges"] and not item["stage_ranges"]:
            raise ob.CheckFailed("Für diese Eingabe sind Messstufen dokumentiert; ausgewertete Stufenbereiche angeben.")
        _subset(item["stage_ranges"],original["stage_ranges"],stage=True)
        for stage in item["stage_ranges"]:
            _subset([stage],[{**s,"utc_offset":stage.get("utc_offset")} for s in item["source_ranges"]])
        windows=[]
        reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")),delimiter="\t")
        headers=tuple(reader.fieldnames);number=0;stamps={}
        for row in reader:
            if tuple(row.get(k) for k in headers)==headers:continue
            number+=1
            stamps[number]=datetime.strptime(row["Datum"]+" "+row["Uhrzeit"],"%d.%m.%Y %H:%M:%S")
        for area in item["source_ranges"]:
            offset=runs._offset(area["utc_offset"])
            windows.append({**deepcopy(area),"first_timestamp_utc":stamps[area["first_record"]].replace(tzinfo=offset).astimezone(timezone.utc).isoformat(),
                            "last_timestamp_utc":stamps[area["last_record"]].replace(tzinfo=offset).astimezone(timezone.utc).isoformat()})
        resolved.append({**deepcopy(item),"dataset_id":actual_id,"dataset_code":ob.field(dataset,"code"),
            "measurement_id":ob.identifier(measurement),"measurement_times":receipt["times"],
            "record_windows":windows,
            "source_receipt":receipt["_server_source"],
            **({"recorded_metadata_gaps":receipt["metadata_gaps"]} if "metadata_gaps" in receipt else {}),
            **({"recorded_measurement_subject":receipt["measurement_subject"], "recorded_subject_evidence":receipt.get("subject_evidence")}
               if "measurement_subject" in receipt else {}),
            "recorded_reference_evidence":receipt.get("reference_evidence",[]),
            "recorded_reference_assessment":receipt.get("reference_assessment")})
    all_resources={x for receipt in cache.values() for values in receipt.get("resources",{}).values() for x in values}
    if any(e["resource_id"] not in all_resources for e in config.get("reference_evidence",[])):
        raise ob.CheckFailed("Referenznachweis ist keiner tatsächlich verwendeten Ressource zugeordnet.")
    for evidence in config.get("reference_evidence",[]):
        if evidence.get("calibration_id"):
            calibration=client.get_sample(evidence["calibration_id"])
            device=client.get_sample(evidence["resource_id"])
            actual=next((v for k,v in ob.props(calibration).items() if ob.propkey(k)=="instrument"),None)
            perm=ob.field(device,"permId")
            if isinstance(perm,dict):perm=perm.get("permId")
            allowed={v for v in (ob.identifier(device),perm) if v}
            if not isinstance(actual,str):actual=ob.identifier(actual)
            if ob.code(ob.field(calibration,"type"))!="CALIBRATION" or actual not in allowed:
                raise ob.CheckFailed("Kalibriernachweis ist dem angegebenen Referenzgerät nicht eindeutig zugeordnet.")
    return resolved


def _native_ids(dataset):
    return {ob.identifier(v) for v in ob.records(dataset.get_parents())}


def ensure_analysis(client,bundle,targets_config):
    config=bundle["config"]
    expected=runs._hash(runs._json({"config":config,"results":bundle["entries"]}))
    if expected!=bundle["sha256"]:raise ob.CheckFailed("Auswertungspaket seit Vorschau verändert.")
    for e in bundle["entries"]:
        if runs._hash((bundle["path"]/e["slot"]/e["filename"]).read_bytes())!=e["sha256"]:
            raise ob.CheckFailed("Ergebnisdatei seit Vorschau verändert.")
    if str(client.url).rstrip("/")!=ob.PLAYGROUND_HOST:raise ob.CheckFailed("Nur BAM-Playground erlaubt.")
    target=runs._targets(targets_config,("analysis",))["analysis"]
    if ob.identifier(client.get_experiment(ob.target_path(target)))!=ob.target_path(target):
        raise ob.CheckFailed("Auswertungs-Collection nicht bestätigt.")
    report=ob.discover_playground(client,targets_config)
    for family,kind in (("object_types","EXPERIMENTAL_STEP"),("dataset_types","ATTACHMENT")):
        if not report[family][kind].get("schema_confirmed"):raise ob.CheckFailed("Auswertungsschema nicht bestätigt.")
    native=config.get("native_dataset_parents",False)
    capability=(targets_config.get("gasi_workflow") or {}).get("native_dataset_parents") or {}
    if native and (capability.get("confirmed") is not True or not capability.get("evidence")):
        raise ob.CheckFailed("Native Dataset-Parents sind für diese Instanz nicht bestätigt.")
    inputs=resolve_inputs(client,config)
    manifest={"schema_version":2,"analysis_id":config["analysis_id"],"inputs":inputs,
              "software_version":config["software_version"],"software_objects":config.get("software_objects",[]),
              "parameters":config["parameters"],"selection_rules":config["selection_rules"],
              "stable_windows":config.get("stable_windows"),"uncertainty":config.get("uncertainty"),
              "requirements":config.get("requirements"),"decision_rule":config.get("decision_rule"),
              "reference_assessment":config["reference_assessment"],"reference_evidence":config.get("reference_evidence",[]),
              "native_dataset_parents":native,"results":bundle["entries"]}
    content=runs._json(manifest);digest=runs._hash(content)
    marker=runs._json({"gasi_analysis":2,"configuration_sha256":bundle["sha256"],"manifest_sha256":digest}).decode("utf-8")
    key="GASI_ANALYSIS_"+runs._hash(config["analysis_id"].encode())[:20].upper()
    schema=report["object_types"]["EXPERIMENTAL_STEP"]
    values={"$NAME":"GaSi Auswertung "+config["analysis_id"],"START_DATE":runs.server_timestamp(config["times"]["start"]),
            "END_DATE":runs.server_timestamp(config["times"]["end"]),"NOTES":marker}
    assignments={a["code"] for a in schema["assignments"]}
    for prop,value in (("REFERENCE",config["analysis_id"]),("EXPERIMENTAL_STEP.EXPERIMENTAL_GOALS",config["purpose"])):
        if prop in assignments:values[prop]=value
    props=ob.mapped_properties(values,schema,report)
    parents={i["measurement_id"] for i in inputs}|set(config.get("software_objects",[]))
    for ref in config.get("software_objects",[]):
        if ob.code(ob.field(client.get_sample(ref),"type")) not in ("SOFTWARE_CODE","JUPYTER_NOTEBOOK"):
            raise ob.CheckFailed("Auswertesoftware-Objekt nicht bestätigt.")
    gateway=ob.PybisGateway(client)
    obj=gateway.find_object(target,"EXPERIMENTAL_STEP",key)
    if obj and (not runs._object_matches(obj,props) or gateway.object_parents(obj)-parents):
        raise ob.CheckFailed("Auswertungskennung existiert mit abweichenden Metadaten/Parents.")
    path=bundle["path"]/"analysis_manifest.json";path.write_bytes(content)
    entries=[*bundle["entries"],{"slot":"analysis_manifest","filename":path.name,"sha256":digest}]
    # Verify existing datasets before repairing or creating anything.
    for entry in entries:
        if obj:
            ds=gateway.find_dataset(obj,"ATTACHMENT",key+"_"+entry["slot"])
            if ds:
                runs._dataset_target(ds,target)
                gateway.verify_dataset_hash(ds,entry["sha256"],entry["filename"])
                if native and _native_ids(ds)-{i["dataset_id"] for i in inputs}:
                    raise ob.CheckFailed("Ergebnisdataset hat zusätzliche Eingabe-Parents.")
    created=obj is None
    if obj is None:obj=gateway.create_object(target,"EXPERIMENTAL_STEP",key,props,sorted(parents))
    for ref in parents-gateway.object_parents(obj):gateway.add_parent(obj,ref)
    obj=gateway.find_object(target,"EXPERIMENTAL_STEP",key)
    if obj is None or not runs._object_matches(obj,props) or gateway.object_parents(obj)!=parents:
        raise ob.CheckFailed("Auswertung oder Parent-Verknüpfung nicht zurückbestätigt.")
    results=[]
    for entry in entries:
        name=key+"_"+entry["slot"]
        ds=gateway.find_dataset(obj,"ATTACHMENT",name);new=ds is None
        if ds is None:
            file=path if entry["slot"]=="analysis_manifest" else bundle["path"]/entry["slot"]/entry["filename"]
            gateway.create_dataset(target,obj,"ATTACHMENT",{"$NAME":name},file)
            ds=gateway.find_dataset(obj,"ATTACHMENT",name)
        if ds is None:raise ob.CheckFailed("Ergebnisdataset nicht zurücklesbar.")
        if native:
            required={i["dataset_id"] for i in inputs}
            if required-_native_ids(ds):
                ds.add_parents(sorted(required-_native_ids(ds)));ds.save()
                ds=client.get_dataset(ob.identifier(ds))
            if _native_ids(ds)!=required:raise ob.CheckFailed("Native Dataset-Parents nicht bestätigt.")
        runs._dataset_target(ds,target)
        gateway.verify_dataset_hash(ds,entry["sha256"],entry["filename"])
        results.append({"dataset_id":ob.identifier(ds),"created":new,"sha256":entry["sha256"],**ob.browser_reference(ds,"dataset")})
    return {"analysis":{"identifier":ob.identifier(obj),"created":created,"collection":ob.target_path(target),
                        **ob.browser_reference(obj,"object")},"inputs":inputs,"results":results,
            "native_dataset_parents_verified":native}


def upload_analysis(*,expected_manifest_sha=None,root=ROOT):
    from gasi_session import writes_enabled
    if not writes_enabled():return None,"Vorschau: keine Auswertung geschrieben."
    try:
        root=Path(root).resolve()
        config=runs.load_run(root/"config/gasi_analysis.json")
        bundle=prepare_analysis(config,root)
        if bundle["sha256"]!=expected_manifest_sha:raise ob.CheckFailed("Auswertung seit Vorschau geändert; erneut prüfen.")
        targets,message=ob.load_target_config(root/"config/playground_test_target.json")
        runs._targets(targets,("analysis",))
        client,message=ob.connect_playground()
        if client is None:return None,message
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            result=ensure_analysis(client,bundle,targets)
        (bundle["path"]/"verification.json").write_bytes(runs._json(result))
        return result,"Auswertung, exakte Eingaben, Parents und Rückdownload-Hashes bestätigt."
    except ob.CheckFailed as exc:return None,str(exc)
    except Exception:return None,"Auswertung unterbrochen; Teilstand mit gleicher analysis_id erneut prüfen. Serverdetails unterdrückt."
