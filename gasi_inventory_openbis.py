"""Preview and explicitly enabled metadata-only registration of documented GaSi devices."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import tempfile

import gasi_openbis_playground as g
from gasi_inventory import ROOT, build_assignment_report, identity_key, manufacturer_key, serial_key, text, write_assignment_report

MARKER = "GASI_DEVICE_INVENTORY_V1"
COLLECTION_NAME = "GaSi: dokumentierte Geräte"
PROPERTIES = ["$NAME", "MANUFACTURER", "DEVICE_MODEL_NAME", "SERIAL_NUMBER", "INVENTORY_NO",
              "INVENTORY_NO_ADD", "BAM_OE", "BAM_LOCATION_COMPLETE", "DESCRIPTION", "NOTES"]


def default_settings():
    return dict(target=dict(space="8.1_EQUIPMENT", project="GASI", collection="INSTRUMENTS"),
                location=dict(code="", confirmed=False, evidence=""),
                )


def load_inventory_settings(path=None):
    config, message = g.load_target_config(path)
    return deepcopy((config or {}).get("gasi_inventory", default_settings())), message


def _atomic_json(path, value, prefix):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=prefix, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_inventory_settings(settings, path=None):
    check_settings(settings)
    path = Path(path) if path is not None else g.TARGET_CONFIG_PATH
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
    else:
        current = json.loads(g.TARGET_TEMPLATE_PATH.read_text(encoding="utf-8"))
    current["gasi_inventory"] = deepcopy(settings)
    _atomic_json(path, current, ".gasi-target-")
    return path


def check_settings(settings):
    if settings.get("target") != default_settings()["target"]:
        raise g.CheckFailed("Geräteanlage ist auf /8.1_EQUIPMENT/GASI/INSTRUMENTS begrenzt.")
    return g.target_path(settings["target"])


def property_value(obj, key):
    values = {g.propkey(k): v for k, v in g.props(obj).items()}
    if isinstance(obj, dict):
        values.update({g.propkey(k): v for k, v in obj.items()})
    return values.get(g.propkey(key))


def identity_from_object(obj):
    return dict(manufacturer=property_value(obj, "MANUFACTURER"), serial_number=property_value(obj, "SERIAL_NUMBER"))


def read_instance(client, settings):
    if str(client.url).rstrip("/") != g.PLAYGROUND_HOST:
        raise g.CheckFailed("Geräteanlage ausschließlich im BAM-Playground erlaubt.")
    report = g.discover_playground(client)
    if report["errors"]:
        raise g.CheckFailed("Bestandsaufnahme unvollständig; vor Geräteanlage Verbindung und Leserechte prüfen.")
    result = client.get_samples(type="INSTRUMENT", attrs=["code", "identifier", "space", "project", "experiment"], props=PROPERTIES)
    instruments = g.table_records(result)
    total = g.field(result, "totalCount")
    if isinstance(total, int) and total != len(instruments):
        raise g.CheckFailed("Instrumentabfrage ist nicht vollständig; keine neuen Geräte anlegen.")
    space_rows = g.table_records(client.get_samples(space=settings["target"]["space"],
        attrs=["code", "identifier", "type"], props=["MANUFACTURER", "SERIAL_NUMBER"]))
    return dict(report=report, instruments=instruments, space_objects=space_rows,
                collection_schema=g.type_details(client, "experiment", "COLLECTION"))


def location_issue(settings, state):
    location = settings.get("location", {})
    if location.get("confirmed") is not True or not text(location.get("evidence")) or not text(location.get("code")):
        return "Tatsächlicher Standort noch nicht belegt: BAM-Standort, Gebäude und Raum erforderlich."
    vocab = state["report"]["vocabularies"].get("BAM_LOCATION_COMPLETE", {})
    if not vocab.get("confirmed") or location["code"] not in {t["code"] for t in vocab["terms"]}:
        return "Standortcode ist nicht in der aktuell bestätigten BAM-Werteliste."
    return None


def device_properties(row, settings):
    notes = dict(scope="Documented GaSi device identity; current installation and calibration status are not confirmed.",
                 evidence=[dict(file=Path(e["file"]).name, sha256=e["sha256"], page=e.get("page"))
                           for e in row["evidence"] if e["verified"]],
                 inventory_reference=row["inventory_number"], open_issues=row["open_issues"],
                 location=deepcopy(settings["location"]))
    values = {"name": f'{row["manufacturer"]} {row["model"]} · SN {row["serial_number"]}',
              "MANUFACTURER": row["manufacturer"], "DEVICE_MODEL_NAME": row["model"],
              "SERIAL_NUMBER": row["serial_number"], "BAM_OE": "OE_8.1",
              "BAM_LOCATION_COMPLETE": settings["location"]["code"],
              "DESCRIPTION": "GaSi-Geräteidentität aus lokalen Belegen. Einbauposition und Prüfmittelstatus separat zu bestätigen.",
              "NOTES": json.dumps(notes, ensure_ascii=False)}
    if row["inventory_number"]:
        main, sub = row["inventory_number"].split("/")
        values.update(INVENTORY_NO=int(main), INVENTORY_NO_ADD=int(sub))
    return values


def prepare_plan(report, settings, state):
    check_settings(settings)
    result = deepcopy(report)
    result["target"] = deepcopy(settings["target"])
    result["location"] = deepcopy(settings.get("location", {}))
    result["location_issue"] = location_issue(settings, state)
    schema = state["report"]["object_types"].get("INSTRUMENT", {})
    for row in result["rows"]:
        row["registration_status"], row["registration_reason"] = "identity_open", ""
        if not row["identity_verified"]:
            continue
        if row.get("openbis_identifier"):
            linked = [obj for obj in state["instruments"] if g.identifier(obj) == row["openbis_identifier"]]
            if len(linked) != 1 or identity_key(identity_from_object(linked[0])) != row["identity_key"]:
                row.update(registration_status="conflict",
                           registration_reason="Gespeicherter openBIS-Verweis ist nicht passend lesbar; vor Neuanlage klären.")
                continue
        serial_matches = [obj for obj in state["instruments"]
                          if serial_key(property_value(obj, "SERIAL_NUMBER")) == serial_key(row["serial_number"])]
        if serial_matches:
            matching = [obj for obj in serial_matches if identity_key(identity_from_object(obj)) == row["identity_key"]]
            if len(serial_matches) != 1 or len(matching) != 1:
                row.update(registration_status="conflict", registration_reason="Seriennummer im Bestand mehrdeutig oder Hersteller abweichend.")
                continue
            obj = matching[0]
            model = text(property_value(obj, "DEVICE_MODEL_NAME"))
            if (model and serial_key(model) != serial_key(row["model"])) or property_value(obj, "BAM_OE") != "OE_8.1":
                row.update(registration_status="conflict", registration_reason="Bestehender Eintrag hat abweichendes Modell oder abweichende OE; nicht verändert.")
                continue
            row.update(registration_status="reuse", openbis=dict(identifier=g.identifier(obj), **g.browser_reference(obj, "object")))
            continue
        collision = any(g.field(obj, "code") == row["suggested_code"] for obj in state["space_objects"])
        if collision:
            row.update(registration_status="conflict", registration_reason="Stabiler Gerätecode ist im Space bereits anderweitig belegt.")
        elif result["location_issue"]:
            row.update(registration_status="location_open", registration_reason=result["location_issue"])
        elif not schema.get("available") or not schema.get("schema_confirmed"):
            row.update(registration_status="schema_open", registration_reason="INSTRUMENT-Typ und Pflichtfelder nicht bestätigt.")
        else:
            try:
                row["properties"] = g.mapped_properties(device_properties(row, settings), schema, state["report"])
                row["registration_status"] = "create"
            except g.CheckFailed as exc:
                row.update(registration_status="schema_open", registration_reason=str(exc))
    return result


def ensure_inventory_collection(client, settings, state):
    path = check_settings(settings)
    if str(client.url).rstrip("/") != g.PLAYGROUND_HOST:
        raise g.CheckFailed("Abweichender Host; keine Geräteanlage.")
    schema = state["collection_schema"]
    if not schema.get("schema_confirmed"):
        raise g.CheckFailed("COLLECTION-Schema unvollständig.")
    properties = g.mapped_properties({"name": COLLECTION_NAME, "$DEFAULT_OBJECT_TYPE": "INSTRUMENT"},
                                    schema, state["report"])
    target = settings["target"]
    project_path = path.rsplit("/", 1)[0]
    projects = g.table_records(client.get_projects(space=target["space"], code=target["project"]))
    projects = [p for p in projects if g.identifier(p) == project_path]
    if len(projects) > 1 or (projects and MARKER not in str(g.field(projects[0], "description", ""))):
        raise g.CheckFailed("Vorhandenes GASI-Projekt ist nicht als dieses Geräteinventar gekennzeichnet; nicht verändert.")
    collections = g.table_records(client.get_experiments(project=project_path, code=target["collection"],
        props=["$NAME", "$DEFAULT_OBJECT_TYPE"])) if projects else []
    collections = [c for c in collections if g.identifier(c) == path]
    if len(collections) > 1 or (collections and (g.code(g.field(collections[0], "type")) != "COLLECTION"
            or g.name(collections[0]) != COLLECTION_NAME or property_value(collections[0], "$DEFAULT_OBJECT_TYPE") != "INSTRUMENT")):
        raise g.CheckFailed("Vorhandene Collection hat abweichende Kennzeichnung; nicht verändert.")
    created = []
    if not projects:
        client.new_project(space=target["space"], code=target["project"],
            description=MARKER + ": documented GaSi device identities; no measurement uploads.").save()
        created.append(project_path)
    if not collections:
        client.new_experiment(type="COLLECTION", code=target["collection"], project=project_path,
            props={k.lower(): v for k, v in properties.items()}).save()
        created.append(path)
    collection = client.get_experiment(path)
    if (g.identifier(collection) != path or g.code(g.field(collection, "type")) != "COLLECTION"
            or g.name(collection) != COLLECTION_NAME or property_value(collection, "$DEFAULT_OBJECT_TYPE") != "INSTRUMENT"):
        raise g.CheckFailed("Inventar-Collection nach Speichern nicht zurückgelesen.")
    return dict(path=path, created=created)


def persist_identifiers(report, root=ROOT):
    path = Path(root) / "config/gasi_setup.json"
    current = json.loads(path.read_text(encoding="utf-8"))
    updated = False
    for row in report["rows"]:
        if not row.get("openbis"):
            continue
        devices = [d for d in current["devices"] if d["position"] == row["position"]]
        if len(devices) != 1 or identity_key(devices[0]) != row["identity_key"]:
            raise g.CheckFailed("Lokale Geräteidentität wurde während der Registrierung geändert; Zuordnung nicht überschrieben.")
        for key, value in (("openbis_identifier", row["openbis"]["identifier"]),
                           ("openbis_perm_id", row["openbis"].get("permId")),
                           ("openbis_url", row["openbis"].get("url"))):
            if value and devices[0].get(key) != value:
                devices[0][key] = value
                updated = True
    if updated:
        _atomic_json(path, current, ".gasi-setup-")


def ensure_devices(client, report, settings, state, root=ROOT):
    plan = prepare_plan(report, settings, state)
    if any(row["registration_status"] == "create" for row in plan["rows"]):
        plan["collection"] = ensure_inventory_collection(client, settings, state)
    gateway = g.PybisGateway(client)
    for row in plan["rows"]:
        if row["registration_status"] == "create":
            existing = gateway.find_object(settings["target"], "INSTRUMENT", row["suggested_code"])
            obj = existing if existing is not None else gateway.create_object(
                settings["target"], "INSTRUMENT", row["suggested_code"], row["properties"])
            if identity_key(identity_from_object(obj)) != row["identity_key"]:
                raise g.CheckFailed("Zurückgelesene Geräteidentität stimmt nicht mit dem Beleg überein.")
            if (serial_key(property_value(obj, "DEVICE_MODEL_NAME")) != serial_key(row["model"])
                    or property_value(obj, "BAM_OE") != "OE_8.1"
                    or property_value(obj, "BAM_LOCATION_COMPLETE") != settings["location"]["code"]):
                raise g.CheckFailed("Modell, OE oder Standort nach Speichern abweichend; unveränderte Identität erneut prüfen.")
            row.update(registration_status="created" if existing is None else "reuse",
                       openbis=dict(identifier=g.identifier(obj), **g.browser_reference(obj, "object")))
        elif row["registration_status"] == "reuse":
            obj = client.get_sample(row["openbis"]["identifier"])
            if identity_key(identity_from_object(obj)) != row["identity_key"]:
                raise g.CheckFailed("Wiederverwendete Geräteidentität hat sich verändert.")
    persist_identifiers(plan, root)
    if any(row["registration_status"] in ("created", "reuse") for row in plan["rows"]):
        plan["registered_at"] = datetime.now(timezone.utc).isoformat()
    return plan


def inspect_inventory(root=ROOT):
    report = build_assignment_report(root)
    settings, message = load_inventory_settings(Path(root) / "config/playground_test_target.json")
    if not report["available"]:
        return report, settings, report["message"]
    client, connection = g.connect_playground()
    if client is None:
        return report, settings, connection
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            plan = prepare_plan(report, settings, read_instance(client, settings))
        return plan, settings, connection + " Gerätebestand ausschließlich gelesen."
    except g.CheckFailed as exc:
        return report, settings, str(exc)
    except Exception:
        return report, settings, "Inventarprüfung unvollständig; Verbindung, Typen und Rechte prüfen. Serverdetails unterdrückt."


def register_inventory(root=ROOT):
    from gasi_session import writes_enabled
    if not writes_enabled():
        return None, "Geräteregistrierung deaktiviert. Nur Vorschau."
    report = build_assignment_report(root)
    if not report["available"]:
        return None, report["message"]
    settings, message = load_inventory_settings(Path(root) / "config/playground_test_target.json")
    client, message = g.connect_playground()
    if client is None:
        return None, message
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = ensure_devices(client, report, settings, read_instance(client, settings), root)
            write_assignment_report(result, Path(root) / "data/datasheets/_auswertung")
        created = sum(r.get("registration_status") == "created" for r in result["rows"])
        reused = sum(r.get("registration_status") == "reuse" for r in result["rows"])
        if created + reused == 0:
            return result, "Keine Geräte angelegt. " + (result.get("location_issue") or "Offene Identitäten oder Bestandskonflikte im lokalen Bericht prüfen.")
        return result, f"Geräte zurückgelesen: {created} angelegt, {reused} wiederverwendet; offene Angaben im lokalen Bericht."
    except g.CheckFailed as exc:
        return None, str(exc)
    except Exception:
        return None, "Geräteanlage unterbrochen. Mit unveränderten Identitäten fortsetzen; Teilstände werden wiederverwendet. Serverdetails unterdrückt."
