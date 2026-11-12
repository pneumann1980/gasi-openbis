"""Create a bounded GaSi Playground test area; no mutations on import/preview."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import io
import json

import gasi_openbis_playground as g
from gasi_playground_targets import save_target_config

PROJECT_CODE = "GASI_TEST"
MARKER = "GASI_PLAYGROUND_TEST_V1"
LOCATION_POLICY = "synthetic_schema_placeholder"
COLLECTIONS = {
    "lab_notebook": ("RUNS", "GaSi TEST: synthetic runs", "EXPERIMENTAL_STEP"),
    "inventory": ("INSTRUMENTS", "GaSi TEST: synthetic instruments", "INSTRUMENT"),
}
CONFIRMATION = "CREATE GASI FB81 PLAYGROUND TEST AREA"
TEST_CONFIG_KEYS = {
    "lab_notebook", "inventory", "approved_test_scope", "instrument", "run_properties",
    "run_code", "dataset_type", "dataset_name", "dataset_properties", "synthetic_location",
}


def proposed_config(lab_space, approval_reference="", location_code="", location_label=""):
    cfg = {key: value for key, value in json.loads(g.TARGET_TEMPLATE_PATH.read_text(encoding="utf-8")).items()
           if key in TEST_CONFIG_KEYS}
    for key, space in (("lab_notebook", lab_space), ("inventory", "8.1_EQUIPMENT")):
        cfg[key] = dict(space=space, project=PROJECT_CODE, collection=COLLECTIONS[key][0])
    cfg["instrument"]["properties"].update(BAM_OE="OE_8.1", BAM_LOCATION_COMPLETE=location_code)
    cfg["instrument"]["properties"]["DESCRIPTION"] = (
        "Synthetic integration-test fixture; NOT a physical device. BAM_LOCATION_COMPLETE "
        "is an API test placeholder, NOT a room assignment. " + MARKER)
    cfg["synthetic_location"] = dict(mode=LOCATION_POLICY, code=location_code, label=location_label,
                                     not_a_physical_assignment=True)
    cfg["approved_test_scope"] = dict(steward_approved=bool(approval_reference.strip()),
        approval_reference=approval_reference.strip(),
        lab_notebook_path_prefix=g.target_path(cfg["lab_notebook"]),
        inventory_path_prefix=g.target_path(cfg["inventory"]))
    return cfg


def _check_scope(client, cfg, confirmation):
    if str(client.url).rstrip("/") != g.PLAYGROUND_HOST:
        raise g.CheckFailed("Einrichtung ausschließlich auf dem BAM-Playground erlaubt.")
    if confirmation != CONFIRMATION:
        raise g.CheckFailed("Einrichtung deaktiviert: ausdrückliche Bestätigung fehlt.")
    scope = cfg.get("approved_test_scope", {})
    if scope.get("steward_approved") is not True or not str(scope.get("approval_reference", "")).strip():
        raise g.CheckFailed("Auftrag/Freigabereferenz für diese beiden Testziele fehlt.")
    for key in COLLECTIONS:
        group = cfg.get(key, {})
        path = g.target_path(group)
        if key == "lab_notebook":
            allowed_space = group["space"].startswith("8.1_") and not any(
                word in group["space"] for word in
                ("EQUIPMENT", "MATERIAL", "METHOD", "PUBLICATION", "STORAGE", "ELN_SETTINGS"))
        else:
            allowed_space = group["space"] == "8.1_EQUIPMENT"
        if not allowed_space or group["project"] != PROJECT_CODE or group["collection"] != COLLECTIONS[key][0]:
            raise g.CheckFailed("Einrichtung ist auf FB-8.1-GASI_TEST mit RUNS/INSTRUMENTS begrenzt.")
        if scope.get(key + "_path_prefix") != path:
            raise g.CheckFailed("Freigabe muss genau die beiden Test-Collections benennen.")
    if cfg.get("instrument", {}).get("type") != "INSTRUMENT":
        raise g.CheckFailed("Einrichtung verwendet den bestätigten Typ INSTRUMENT.")
    location = cfg.get("synthetic_location", {})
    if (location.get("mode") != LOCATION_POLICY or location.get("not_a_physical_assignment") is not True
            or not location.get("code") or cfg["instrument"].get("properties", {}).get("BAM_LOCATION_COMPLETE") != location["code"]
            or MARKER not in cfg["instrument"]["properties"].get("DESCRIPTION", "")):
        raise g.CheckFailed("Standort muss ausdrücklich als technischer Test-Platzhalter dokumentiert sein.")


def _existing(client, cfg):
    """Search before create; connection/rights errors are never treated as absence."""
    found = {}
    for key, (_, title, object_type) in COLLECTIONS.items():
        group = cfg[key]
        project_path = f"/{group['space']}/{PROJECT_CODE}"
        projects = [p for p in g.records(client.get_projects(space=group["space"], code=PROJECT_CODE))
                    if g.identifier(p) == project_path]
        if len(projects) > 1 or (projects and MARKER not in str(g.field(projects[0], "description", ""))):
            raise g.CheckFailed(f"{project_path}: vorhandenes Projekt trägt nicht den GaSi-Testmarker.")
        collections = [c for c in g.records(client.get_experiments(project=project_path, code=group["collection"]))
                       if g.identifier(c) == g.target_path(group)] if projects else []
        if len(collections) > 1 or (collections and (g.code(g.field(collections[0], "type")) != "COLLECTION"
                or g.name(collections[0]) != title
                or g.props(collections[0]).get("$default_object_type", g.props(collections[0]).get("$DEFAULT_OBJECT_TYPE")) != object_type)):
            raise g.CheckFailed(f"{g.target_path(group)}: vorhandene Collection hat abweichenden Typ/Testmarker.")
        found[key] = (projects, collections)
    return found


def ensure_test_area(client, config, confirmation):
    """Idempotent provisioning; retries recover saves whose response was lost."""
    cfg = deepcopy(config)
    _check_scope(client, cfg, confirmation)
    found = _existing(client, cfg)
    schema = g.type_details(client, "experiment", "COLLECTION")
    if not schema["schema_confirmed"]:
        raise g.CheckFailed("COLLECTION-Typ und Pflichtfelder nicht lesend bestätigt.")
    report = g.discover_playground(client, cfg)
    vocab = report["vocabularies"].get("BAM_LOCATION_COMPLETE", {})
    if not vocab.get("confirmed"):
        raise g.CheckFailed("Standort-Werteliste nicht lesbar; kein neuer Wert wird geraten.")
    g.validate_target(report, cfg, require_existing_targets=False)
    collection_props = {key: g.mapped_properties({"name": title, "$DEFAULT_OBJECT_TYPE": object_type}, schema, report)
                        for key, (_, title, object_type) in COLLECTIONS.items()}
    created = []
    for key, (_, title, _) in COLLECTIONS.items():
        group = cfg[key]
        project_path = f"/{group['space']}/{PROJECT_CODE}"
        projects, collections = found[key]
        if not projects:
            client.new_project(space=group["space"], code=PROJECT_CODE,
                description=MARKER + ": GaSi FB 8.1 synthetic Playground integration tests only.").save()
            created.append(project_path)
        if not collections:
            client.new_experiment(type="COLLECTION", code=group["collection"], project=project_path,
                props={k.lower(): v for k, v in collection_props[key].items()}).save()
            created.append(g.target_path(group))
    _existing(client, cfg)
    for key in COLLECTIONS:
        collection = client.get_experiment(g.target_path(cfg[key]))
        report["targets"][key] = {"path": g.identifier(collection), "visible": True}
    g.validate_target(report, cfg)
    return {"config": cfg, "created": created, "targets": report["targets"],
            "location_code": cfg["synthetic_location"]["code"], "location_is_placeholder": True,
            "verified_at": datetime.now(timezone.utc).isoformat()}


def provision_playground(config, confirmation="", config_path=None):
    """Notebook boundary; sanitized errors, central JSON written only after readback."""
    if confirmation != CONFIRMATION:
        return None, "Einrichtung deaktiviert. Nur Vorschau; keine Playground-Einträge angelegt."
    client, message = g.connect_playground()
    if client is None:
        return None, message
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = ensure_test_area(client, config, confirmation)
            current, _ = g.load_target_config() if config_path is None else g.load_target_config(config_path)
            merged = deepcopy(current) if current is not None else {}
            merged.update({key: value for key, value in result["config"].items() if key in TEST_CONFIG_KEYS})
            save_target_config(merged, config_path)
        return result, "FB-8.1-Testbereich zurückgelesen und zentrale Ziel-JSON gespeichert."
    except g.CheckFailed as exc:
        return None, str(exc)
    except Exception:
        return None, ("Einrichtung unterbrochen: Rechte, Verbindung oder Server-Validator prüfen. "
                      "Mit derselben Konfiguration fortsetzen; keine Rollenänderung und keine Löschung. "
                      "Teilschritte können bereits gespeichert sein; Serverdetails bleiben unterdrückt.")
