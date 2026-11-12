"""Den aktuellen GaSi-Aufbau lokal prüfen; keine Verbindung und kein Geräteimport."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETUP_PATH = ROOT / "config/gasi_setup.json"
REPORT_PATH = ROOT / "data/datasheets/_auswertung/GaSi_Aktuelles_Setup.html"


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def inspect_setup(path=SETUP_PATH):
    """Unbekannte Geräteangaben bleiben offen; Bestätigung wird niemals abgeleitet."""
    path = Path(path)
    if not path.is_file():
        return {"available": False, "ready": False, "devices": [], "channels": [],
                "message": "config/gasi_setup.json fehlt. config/gasi_setup.example.json lokal kopieren und den aktuellen Aufbau eintragen."}
    raw = path.read_bytes()
    try:
        setup = json.loads(raw)
        if (not isinstance(setup, dict) or setup.get("schema_version") != 1
                or setup.get("scope") != "current_only" or not isinstance(setup.get("setup_id"), str)
                or not setup["setup_id"].strip()):
            raise ValueError
        modules = setup["modules"]
        devices = setup["devices"]
        channels = setup.get("channels", [])
        if (not isinstance(modules, dict) or not modules or not isinstance(devices, list)
                or not devices or not isinstance(channels, list)):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise ValueError("Setup benötigt schema_version=1, scope=current_only, setup_id, modules und devices.") from None

    positions, serials, rows = set(), set(), []
    for device in devices:
        if not isinstance(device, dict):
            raise ValueError("Jede Geräteposition muss ein JSON-Objekt sein.")
        position = device.get("position")
        if not isinstance(position, str) or not position.strip() or position in positions:
            raise ValueError("Geräteposition fehlt oder kommt mehrfach vor.")
        positions.add(position)
        if device.get("module") not in modules:
            raise ValueError("Eine Geräteposition verweist auf ein unbekanntes Modul.")
        serial = device.get("serial_number")
        if serial is not None and not isinstance(serial, str):
            raise ValueError("Seriennummern als Text oder null angeben.")
        if serial and serial.strip():
            normalized = serial.strip().casefold()
            if normalized in serials:
                raise ValueError("Eine Seriennummer ist mehreren Gerätepositionen zugewiesen.")
            serials.add(normalized)
        issues = device.get("open_issues", [])
        if not isinstance(issues, list) or any(not isinstance(i, str) for i in issues):
            raise ValueError("open_issues muss eine Liste von Texten sein.")
        issues = list(issues)
        for field, label in (("manufacturer", "Hersteller"), ("model", "Modell"), ("serial_number", "Seriennummer/Gerätekennung")):
            if not isinstance(device.get(field), str) or not device[field].strip():
                issues.append(label + " fehlt.")
        if device.get("installed_confirmed") is not True:
            issues.append("Identität an dieser Position im aktuellen Aufbau noch nicht bestätigt.")
        if not device.get("evidence"):
            issues.append("Beleg zur Geräteidentität fehlt.")
        if device.get("kind") in ("mfc", "mfm", "pressure_controller"):
            upper = device.get("range_max")
            if not _finite(upper) or upper <= 0 or not device.get("unit"):
                issues.append("Dokumentierter Bereich/Einheit fehlt oder ist ungültig.")
        if device.get("quantity") == "normal_volume_flow":
            temp, pressure = device.get("reference_temperature_C"), device.get("reference_pressure_hPa_abs")
            if not _finite(temp) or temp <= -273.15 or not _finite(pressure) or pressure <= 0:
                issues.append("Bezugsbedingungen des Normalvolumenstroms fehlen oder sind ungültig.")
            for field in ("design_gas", "calibration_medium", "operation_gas"):
                if not device.get(field):
                    issues.append({"design_gas": "Auslegungsgas", "calibration_medium": "Kalibriermedium", "operation_gas": "Betriebsgas"}[field] + " noch offen.")
        if device.get("calibration_status") != "assessed":
            issues.append("Aktueller Kalibrier-/Prüfmittelstatus noch nicht bewertet.")
        rows.append({**device, "issues": issues, "ready": not issues})

    channel_names, channel_rows = set(), []
    for channel in channels:
        if (not isinstance(channel, dict) or not isinstance(channel.get("name"), str)
                or not channel["name"].strip() or channel["name"] in channel_names
                or channel.get("device_position") not in positions):
            raise ValueError("Kanalname fehlt/ist doppelt oder die Geräteposition ist unbekannt.")
        channel_names.add(channel["name"])
        channel_rows.append({**channel, "ready": channel.get("confirmed") is True and bool(channel.get("measurement_location"))})
    verified_on = setup.get("verified_on")
    if verified_on is not None:
        try:
            date.fromisoformat(verified_on)
        except (TypeError, ValueError):
            raise ValueError("verified_on als ISO-Datum YYYY-MM-DD oder null angeben.") from None
    ready = all(d["ready"] for d in rows) and all(c["ready"] for c in channel_rows) and bool(verified_on)
    return {"available": True, "ready": ready, "setup_id": setup["setup_id"], "name": setup.get("name", "GaSi"),
            "sha256": sha256(raw).hexdigest(), "source": path, "modules": modules, "devices": rows,
            "channels": channel_rows, "verified_on": verified_on,
            "message": "Aktuelles Setup lokal geprüft; keine openBIS-Bestätigung und keine Registrierung."}


def measurement_context(report):
    """Aktuelles Setup als Vorschlag; vorhandene CSVs werden ihm nicht zugewiesen."""
    if not report.get("available"):
        return None
    return {"setup_id": report["setup_id"], "configuration_sha256": report["sha256"],
            "setup_checked_locally": report["ready"], "applies_to_source_file": False,
            "association_status": "unassigned; the current setup does not prove which setup produced a file"}


def show_setup_summary(report):
    """Keine Seriennummern, Beleginhalte oder Konfliktdetails in Notebook-Ausgaben."""
    print(report["message"])
    if report.get("available"):
        ready = sum(d["ready"] for d in report["devices"])
        print(f"Gerätepositionen: {len(report['devices'])}; lokal vollständig geprüft: {ready}.")
        print(f"Kanalzuordnungen: {len(report['channels'])}; aktuell bestätigt: {sum(c['ready'] for c in report['channels'])}.")
        print("Gesamtstand:", "lokal bestätigt" if report["ready"] else "Entwurf mit offenen Angaben")
        print("Seriennummern und konkrete offene Angaben stehen nur im lokalen HTML-Bericht.")


def write_setup_report(report, path=REPORT_PATH):
    """Lokale, eigenständige Lesefassung; alle eingelesenen Texte werden escaped."""
    if not report.get("available"):
        return None
    path = Path(path)
    if path.resolve() == Path(report["source"]).resolve():
        raise ValueError("Der Bericht darf die Setup-Konfiguration nicht überschreiben.")
    def value(v):
        return escape(str(v)) if v is not None and v != "" else "offen"
    rows = []
    for d in report["devices"]:
        area = report["modules"][d["module"]]
        facts = " · ".join(value(d.get(k)) for k in ("manufacturer", "model", "serial_number"))
        flow = f"{value(d.get('range_max'))} {value(d.get('unit'))}" if d.get("kind") in ("mfc", "mfm", "pressure_controller") else "—"
        notes = (f'<details><summary>{len(d["issues"])} offene Angaben</summary><ul>'
                 + "".join("<li>" + escape(i) + "</li>" for i in d["issues"]) + "</ul></details>") if d["issues"] else "lokal bestätigt"
        rows.append(f"<tr><td><b>{value(d['position'])}</b><br>{value(area)}</td><td>{facts}</td><td>{flow}</td><td>{notes}</td></tr>")
    channel_rows = "".join(f"<tr><td>{value(c['name'])}</td><td>{value(c['device_position'])}</td><td>{value(c.get('measurement_location'))}</td><td>{'bestätigt' if c['ready'] else 'offen'}</td></tr>" for c in report["channels"])
    document = '''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GaSi – aktuelles Setup</title><style>body{font:17px/1.5 system-ui,sans-serif;color:#183448;max-width:1100px;margin:30px auto;padding:0 18px}h1{font-size:1.8rem}.note{background:#fff5dc;padding:15px}table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{border:1px solid #ccd9df;padding:12px;text-align:left;vertical-align:top}th{background:#eef5f7}ul{padding-left:20px;margin:0}details{margin:18px 0}summary{cursor:pointer;font-weight:600}.table{overflow:auto}footer{font-size:.8rem;color:#52636c}</style>
<h1>GaSi: aktuelles Setup</h1><p class="note">Nur lokal. Einträge sind Vorbereitung, keine registrierten Geräte. Fehlende Angaben bleiben offen.</p>'''
    document += f"<p>{len(rows)} Gerätepositionen · {'lokal bestätigt' if report['ready'] else 'Entwurf – offene Punkte unten'}</p>"
    document += '<div class="table"><table><tr><th>Position / Modul</th><th>Gerät / Seriennummer</th><th>Dokumentierter Endwert</th><th>Aktuell zu klären</th></tr>' + "".join(rows) + '</table></div>'
    document += '<details><summary>Kanalzuordnungen</summary><div class="table"><table><tr><th>Kanal</th><th>Geräteposition</th><th>Messort</th><th>Status</th></tr>' + channel_rows + '</table></div></details>'
    document += '<footer>Quelle: lokale config/gasi_setup.json · SHA-256: ' + escape(report["sha256"]) + '</footer></html>'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
