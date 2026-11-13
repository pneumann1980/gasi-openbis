"""Use an existing sensor identity or register one documented DUT, without raw data."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path

import gasi_openbis_playground as ob
import gasi_session as session
import gasi_run as runs
from gasi_inventory_openbis import _atomic_json

ROOT = Path(__file__).resolve().parent
ALLOWED = ("SAMPLE", "TEST_OBJECT", "INSTRUMENT")


def _matches(obj, expected):
    actual = {ob.propkey(k): v for k, v in ob.props(obj).items()}
    return all(actual.get(ob.propkey(k)) == v for k, v in expected.items())


def ensure_dut(client, config, targets):
    if str(client.url).rstrip("/") != ob.PLAYGROUND_HOST:
        raise ob.CheckFailed("Prüfling nur im BAM-Playground verwalten.")
    if config.get("identifier"):
        obj = client.get_sample(config["identifier"])
        if ob.identifier(obj) != config["identifier"] or not any(
                ob.code(ob.field(obj, "type")) == t or ob.code(ob.field(obj, "type")).startswith(t + ".") for t in ALLOWED):
            raise ob.CheckFailed("Vorhandener Prüfling ist nicht eindeutig lesbar oder hat einen ungeeigneten Typ.")
        return obj, False
    if not config.get("local_id") or not config.get("name") or config.get("type") not in ALLOWED:
        raise ob.CheckFailed("Vorhandene identifier angeben oder local_id, name und geeigneten Typ eintragen.")
    target = (targets.get("gasi_dut") or {}).get("target", {})
    path = ob.target_path(target)
    if target["space"] != "8.1_EQUIPMENT" or target["project"] != "GASI":
        raise ob.CheckFailed("Neue Prüflinge nur im konfigurierten FB-8.1-GaSi-Inventar anlegen.")
    if ob.identifier(client.get_experiment(path)) != path:
        raise ob.CheckFailed("Prüflingscollection fehlt; einmalige Einrichtung ausführen.")
    report = ob.discover_playground(client, targets)
    schema = ob.type_details(client, "sample", config["type"])
    if not schema.get("schema_confirmed"):
        raise ob.CheckFailed("Prüflingstyp mit Pflichtfeldern nicht bestätigt.")
    values = {**config.get("properties", {}), "$NAME": config["name"], "BAM_OE": "OE_8.1"}
    props = ob.mapped_properties(values, schema, report)
    code = "GASI_DUT_" + runs._hash(config["local_id"].encode())[:20].upper()
    gateway = ob.PybisGateway(client)
    obj = gateway.find_object(target, config["type"], code)
    if obj is not None and not _matches(obj, props):
        raise ob.CheckFailed("Diese Prüflingskennung existiert mit abweichenden Metadaten; keinen zweiten Eintrag erzeugt.")
    collision = [v for v in ob.table_records(client.get_samples(space=target["space"], code=code, attrs=["identifier"]))
                 if obj is None or ob.identifier(v) != ob.identifier(obj)]
    if collision:
        raise ob.CheckFailed("Prüflingscode ist im Inventar anderweitig belegt.")
    created = obj is None
    if created:
        gateway.create_object(target, config["type"], code, props)
    obj = gateway.find_object(target, config["type"], code)
    if obj is None or not _matches(obj, props):
        raise ob.CheckFailed("Prüfling wurde nicht passend zurückgelesen.")
    return obj, created


def manage_dut(root=ROOT):
    root = Path(root)
    result = {"mode": session.mode_status(), "planned": []}
    try:
        path = root / "config/gasi_pruefling.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        reference = config.get("identifier")
        result["planned"] = ["Vorhandenen Prüfling verwenden: " + reference] if reference else [
            "Prüfling registrieren: " + str(config.get("name")), "Typ: " + str(config.get("type"))]
        if not reference and (not config.get("local_id") or not config.get("name")):
            raise ob.CheckFailed("Prüfling fehlt: config/gasi_pruefling.json ausfüllen; vorhandene Objekt-ID bevorzugen.")
        if not session.writes_enabled():
            return result, "Vorschau: Prüflingsidentität würde geprüft und für die Messung übernommen; nichts in openBIS geändert."
        targets, message = ob.load_target_config(root / "config/playground_test_target.json")
        if targets is None:
            raise ob.CheckFailed(message)
        client, message = ob.connect_playground()
        if client is None:
            return result, message
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            obj, created = ensure_dut(client, config, targets)
        config["identifier"] = ob.identifier(obj)
        _atomic_json(path, config, ".gasi-setup-")
        runpath = root / "config/gasi_run.json"
        run = runs.load_run(runpath)
        assignment = "Laufvorlage nicht vorhanden."
        if run is not None:
            old = (run.get("dut") or {}).get("identifier")
            if not old or old == config["identifier"]:
                run["dut"] = dict(identifier=config["identifier"], kind=config.get("kind", "gas_humidity_sensor"), identity_confirmed=True)
                _atomic_json(runpath, run, ".gasi-setup-")
                assignment = "Prüfling in config/gasi_run.json eingetragen."
            else:
                assignment = "Vorhandene andere Prüflingszuordnung im Lauf beibehalten; neuen Lauf separat konfigurieren."
        result["pruefling"] = dict(identifier=ob.identifier(obj), created=created, **ob.browser_reference(obj, "object"))
        return result, "Prüfling zurückgelesen. " + assignment
    except ob.CheckFailed as exc:
        return result, str(exc)
    except (OSError, ValueError, TypeError):
        return result, "Lokale Prüflingskonfiguration fehlt oder ist ungültig. Einmalige Einrichtung ausführen."
    except Exception:
        return result, "Prüflingsverwaltung unterbrochen; mit gleicher local_id erneut ausführen. Serverdetails unterdrückt."
