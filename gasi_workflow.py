"""Three user entry points; one shared session switch, no per-notebook approvals."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path

import gasi_openbis_playground as ob
import gasi_session as session
import gasi_playground_provision as provision
import gasi_inventory_openbis as inventory
import gasi_run as runs
from gasi_playground_targets import save_target_config

ROOT = Path(__file__).resolve().parent


def initialize_local(root=ROOT):
    """Only missing local templates; never replace user configuration."""
    root = Path(root)
    created = []
    for name in ("playground_test_target", "gasi_setup", "gasi_run", "gasi_analysis", "gasi_pruefling"):
        target = root / "config" / (name + ".json")
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("xb") as stream:
                    stream.write((root / "config" / (name + ".example.json")).read_bytes())
                created.append(target.name)
            except FileExistsError:
                pass
    return created


def configured_targets(config):
    """Derive named GaSi collections only from the explicitly configured projects."""
    if not isinstance(config, dict):
        raise ob.CheckFailed("Ziele fehlen: config/playground_test_target.json einmalig einrichten.")
    cfg = deepcopy(config)
    lab = cfg.get("lab_notebook", {})
    lab_path = ob.target_path(lab)
    if not lab["space"].startswith("8.1_") or "EQUIPMENT" in lab["space"]:
        raise ob.CheckFailed("Laborbuchziel muss in einem konfigurierten FB-8.1-Laborbuchspace liegen.")
    inv = cfg.setdefault("gasi_inventory", inventory.default_settings())
    inventory.check_settings(inv)
    workflow = cfg.setdefault("gasi_workflow", {})
    if workflow.get("host", ob.PLAYGROUND_HOST) != ob.PLAYGROUND_HOST:
        raise ob.CheckFailed("Nur der BAM-Playground ist zulässig.")
    workflow["host"] = ob.PLAYGROUND_HOST
    targets = workflow.setdefault("targets", {})
    for key, group in (("measurement", lab), ("preparation", lab),
                       ("analysis", {**lab, "collection": "ANALYSES"})):
        if not all((targets.get(key) or {}).get(k) for k in ("space", "project", "collection")):
            targets[key] = deepcopy(group)
    if not workflow.get("lab_project"):
        workflow["lab_project"] = (workflow.get("approved_scope") or {}).get("lab_path_prefix") or lab_path.rsplit("/", 1)[0]
    workflow.pop("approved_scope", None)
    inv.pop("authorization", None)
    cfg.pop("approved_test_scope", None)
    cfg["test_scope"] = {key + "_path_prefix": ob.target_path(cfg[key]) for key in ("lab_notebook", "inventory")}
    runs._targets(cfg)
    cfg.setdefault("gasi_dut", {"target": {**inv["target"], "collection": "PRUEFLINGE"}})
    dut_path = ob.target_path(cfg["gasi_dut"]["target"])
    if not dut_path.startswith(ob.target_path(inv["target"]).rsplit("/", 1)[0] + "/"):
        raise ob.CheckFailed("Prüflingscollection muss im konfigurierten GaSi-Inventarprojekt liegen.")
    return cfg


def collection_plan(client, target, name, object_type, schema, report):
    """Read every existing collection before saving; foreign collections are never changed."""
    path = ob.target_path(target)
    project = path.rsplit("/", 1)[0]
    rows = [v for v in ob.table_records(client.get_experiments(project=project, code=target["collection"],
             props=["$NAME", "$DEFAULT_OBJECT_TYPE"])) if ob.identifier(v) == path]
    if len(rows) > 1:
        raise ob.CheckFailed("Collection ist nicht eindeutig.")
    if rows and (ob.code(ob.field(rows[0], "type")) != "COLLECTION" or ob.name(rows[0]) != name or
                 inventory.property_value(rows[0], "$DEFAULT_OBJECT_TYPE") != object_type):
        raise ob.CheckFailed("Bestehende Collection hat abweichende Kennzeichnung: " + path)
    props = ob.mapped_properties({"name": name, "$DEFAULT_OBJECT_TYPE": object_type}, schema, report)
    return dict(path=path, target=target, props=props, exists=bool(rows))


def ensure_collection(client, plan):
    if not plan["exists"]:
        target = plan["target"]
        client.new_experiment(type="COLLECTION", code=target["collection"],
            project=plan["path"].rsplit("/", 1)[0],
            props={k.lower(): v for k, v in plan["props"].items()}).save()
    result = client.get_experiment(plan["path"])
    if ob.identifier(result) != plan["path"] or any(
            inventory.property_value(result, k) != v for k, v in plan["props"].items()):
        raise ob.CheckFailed("Collection nicht passend zurückgelesen.")
    return dict(path=plan["path"], created=not plan["exists"])


def setup_project(root=ROOT):
    """Setup only; never consumes a real measurement or creates a DUT identity."""
    root = Path(root)
    result = {"mode": session.mode_status(), "local_templates": initialize_local(root), "planned": []}
    try:
        config, message = ob.load_target_config(root / "config/playground_test_target.json")
        cfg = configured_targets(config)
        result["planned"] = [
            "Testbereich bereitstellen: " + ob.target_path(cfg["lab_notebook"]),
            "Synthetisches Testinventar: " + ob.target_path(cfg["inventory"]),
            "Belegte Geräte abgleichen: " + ob.target_path(cfg["gasi_inventory"]["target"]),
            "Messziel: " + ob.target_path(cfg["gasi_workflow"]["targets"]["measurement"]),
            "Auswertungsziel: " + ob.target_path(cfg["gasi_workflow"]["targets"]["analysis"]),
            "Prüflingsziel: " + ob.target_path(cfg["gasi_dut"]["target"]),
            "Synthetischen CSV-Schreibtest mit Rückdownload und Hashvergleich ausführen.",
        ]
        if not session.writes_enabled():
            return result, "Vorschau der einmaligen Einrichtung; nichts in openBIS geändert."
        client, message = ob.connect_playground()
        if client is None:
            return result, message
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            # Bounded test targets and existing object markers are rechecked before mutations.
            provision._check_scope(client, cfg)
            provision._existing(client, cfg)
            state = inventory.read_instance(client, cfg["gasi_inventory"])
            if inventory.location_issue(cfg["gasi_inventory"], state):
                raise ob.CheckFailed(inventory.location_issue(cfg["gasi_inventory"], state))
            schema = state["collection_schema"]
            if not schema.get("schema_confirmed"):
                raise ob.CheckFailed("COLLECTION-Schema nicht bestätigt.")
            analysis_target = cfg["gasi_workflow"]["targets"]["analysis"]
            extra = [(cfg["gasi_dut"]["target"], "GaSi: Prüflinge", "SAMPLE")]
            if ob.target_path(analysis_target) != ob.target_path(cfg["lab_notebook"]):
                extra.append((analysis_target, "GaSi: Auswertungen", "EXPERIMENTAL_STEP"))
            plans = [collection_plan(client, *item, schema, state["report"]) for item in extra]
            # Custom measurement/preparation targets must already exist; only documented defaults are created.
            for key, target in cfg["gasi_workflow"]["targets"].items():
                if key != "analysis" and ob.target_path(target) != ob.target_path(cfg["lab_notebook"]):
                    if ob.identifier(client.get_experiment(ob.target_path(target))) != ob.target_path(target):
                        raise ob.CheckFailed("Zusätzliches Forschungsziel nicht bestätigt.")
            result["test_area"] = provision.ensure_test_area(client, cfg)
            result["inventory_collection"] = inventory.ensure_inventory_collection(client, cfg["gasi_inventory"], state)
            result["collections"] = [ensure_collection(client, plan) for plan in plans]
            # Persist only after target readback; interrupted saves are recognized on repetition.
            save_target_config(cfg, root / "config/playground_test_target.json")
            report = inventory.build_assignment_report(root)
            if report.get("available"):
                registered = inventory.ensure_devices(client, report, cfg["gasi_inventory"],
                    inventory.read_instance(client, cfg["gasi_inventory"]), root)
                inventory.write_assignment_report(registered, root / "data/datasheets/_auswertung")
                result["devices"] = {label: sum(r.get("registration_status") == label for r in registered["rows"])
                                     for label in ("created", "reuse", "identity_open", "conflict")}
            checked = ob.validate_target(ob.discover_playground(client, cfg), cfg)
            import tempfile
            with tempfile.TemporaryDirectory(prefix="gasi-setup-test-") as temp:
                csv = Path(temp) / "gasi_synthetic_test.csv"
                csv.write_bytes(ob.TEST_CSV_BYTES)
                result["synthetic_test"] = ob.ensure_synthetic_test(ob.PybisGateway(client), checked, csv)
        return result, "Einrichtung und synthetischer Rückdownload bestätigt. Echte Messdaten wurden nicht gelesen oder hochgeladen."
    except ob.CheckFailed as exc:
        return result, str(exc)
    except Exception:
        return result, "Einrichtung unvollständig: Ziele, Rechte, Standort und Verbindung prüfen; mit derselben Konfiguration fortsetzen. Serverdetails unterdrückt."


def upload_measurement(root=ROOT):
    """Always show a meaningful local plan, then honor the one central write switch."""
    root = Path(root)
    result = {"mode": session.mode_status(), "planned": [], "issues": []}
    try:
        run = runs.load_measurement(root / "config/gasi_run.json")
    except ob.CheckFailed as exc:
        result["issues"] = [str(exc)]
        return result, "Laufkonfiguration korrigieren; keine Änderungen in openBIS."
    result["issues"] = runs.validate_run(run, root)
    result["metadata_gaps"] = runs.metadata_gaps(run) if (run or {}).get("metadata_profile") == "raw_capture" else []
    config, _ = ob.load_target_config(root / "config/playground_test_target.json")
    try:
        targets = runs._targets(config, runs.activities(run) if run else ("measurement",))
        result["planned"] = ["Messziel: " + ob.target_path(targets["measurement"])]
    except ob.CheckFailed as exc:
        result["issues"].append(str(exc))
    if run:
        result["planned"] += ["Lauf: " + str(run.get("run_id")), "Prüfling: " + str((run.get("dut") or {}).get("identifier")),
                              "Unveränderte Originaldateien: " + str(len((run.get("files") or {}).get("raw_data", [])))]
    if result["issues"]:
        return result, "Messung noch unvollständig; fehlende Angaben ergänzen."
    try:
        bundle = runs.prepare_bundle(run, root)
        result["manifest_sha256"] = bundle["sha256"]
        result["planned"] += [e["type"] + ": " + e["filename"] for e in bundle["manifest"]["datasets"]]
        if not session.writes_enabled():
            return result, "Vorschau geprüft: Messung, Parents und Datasets würden registriert; nichts in openBIS geändert."
        verification, message = runs.upload_workflow(expected_manifest_sha=bundle["sha256"], root=root)
        result["verification"] = verification
        return result, message
    except ob.CheckFailed as exc:
        return result, str(exc)


def generate_model(root=ROOT):
    """Offline documentation only; available independently of session or server setup."""
    import gasi_model_html
    root = Path(root)
    source = root / "docs/GaSi_Datenmodell.md"
    detailed = gasi_model_html.generate_html(source)
    concept = root / "docs/GaSi_Konzeptmodell.html"
    return dict(concept=concept, details=detailed) if concept.is_file() else dict(details=detailed)


def show_result(result, message):
    """Concise user output; IDs and browser links without full device evidence."""
    print(result.get("mode", session.mode_status()))
    for line in result.get("planned", []):
        print("-", line)
    if result.get("issues"):
        print("Vor der Ausführung klären:")
        for line in result["issues"]:
            print("-", line)
    if result.get("metadata_gaps"):
        print("Im Laufkontext als offen dokumentiert:")
        for line in result["metadata_gaps"]:
            print("-", line)
    print(message)
    for key in ("collections", "devices", "synthetic_test", "verification", "pruefling"):
        if result.get(key):
            print(key + ":", result[key])
