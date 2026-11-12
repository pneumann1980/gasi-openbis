"""Local device identities and asset-number candidates; never uploads source files."""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import csv
import io
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
REPORT_DIRECTORY = ROOT / "data/datasheets/_auswertung"
REPORT_NAME = "GaSi_Geraetezuordnung"


def text(value):
    return value.strip() if isinstance(value, str) else ""


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text(value)).casefold())


def serial_key(value):
    # Punctuation can distinguish actual serial numbers; remove whitespace only.
    return re.sub(r"\s+", "", text(value)).casefold()


def manufacturer_key(value):
    value = normalized(value)
    return next((brand for brand in ("bronkhorst", "alicat", "mbw", "keller") if value.startswith(brand)), value)


def identity_key(device):
    manufacturer, serial = manufacturer_key(device.get("manufacturer")), serial_key(device.get("serial_number"))
    return f"{manufacturer}\0{serial}" if manufacturer and serial else ""


def device_code(device):
    key = identity_key(device)
    if not key:
        return None
    return "GASI_INSTR_" + sha256(key.encode("utf-8")).hexdigest()[:16].upper()


def read_register(path):
    raw = Path(path).read_bytes()
    try:
        source = raw.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        source, encoding = raw.decode("cp1252"), "cp1252"
    rows = list(csv.reader(io.StringIO(source), delimiter=";", strict=True))
    required = ["Inventarnummer", "OE", "Preis", "Leistungsbeschreibung"]
    if not rows or rows[0] != required or any(len(row) != 4 for row in rows[1:]):
        raise ValueError("Inventar-CSV benötigt vier vollständige Spalten: Inventarnummer;OE;Preis;Leistungsbeschreibung.")
    result, numbers = [], set()
    for line, row in enumerate(rows[1:], 2):
        if not re.fullmatch(r"\d+/\d+", row[0]) or row[0] in numbers:
            raise ValueError(f"Inventar-CSV: ungültige oder doppelte Inventarnummer in Zeile {line}.")
        numbers.add(row[0])
        # Excel's quoted OE is data. No formulas are evaluated; prices are omitted.
        oe = row[1].strip()
        match = re.fullmatch(r'="\s*([^"]+)"', oe)
        result.append(dict(number=row[0], organization=(match.group(1).strip() if match else oe),
                           description=row[3], source_line=line))
    return dict(source=str(path), sha256=sha256(raw).hexdigest(), encoding=encoding, rows=result)


def verify_identity(device, root, page_cache=None):
    fields = ("manufacturer", "model", "serial_number")
    missing = [field for field in fields if not text(device.get(field))]
    if missing:
        return False, [], ["Identitätsangaben fehlen: " + ", ".join(missing)]
    checks = []
    page_cache = page_cache if page_cache is not None else {}
    private_root = (root / "data/datasheets").resolve()
    for evidence in device.get("evidence", []):
        source = evidence.get("file", "")
        path = (root / source).resolve()
        check = dict(file=source, page=evidence.get("page"), verified=False)
        if not path.is_relative_to(private_root) or not path.is_file():
            check["reason"] = "Beleg fehlt oder liegt außerhalb der lokalen Geräteunterlagen."
            checks.append(check)
            continue
        digest = sha256(path.read_bytes()).hexdigest()
        check["sha256"] = digest
        if path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
                page = evidence.get("page", 1)
                if not isinstance(page, int) or isinstance(page, bool) or page < 1:
                    raise ValueError
                key = (str(path), digest, page)
                if key not in page_cache:
                    page_cache[key] = PdfReader(path).pages[page-1].extract_text() or ""
                content = normalized(page_cache[key])
                check.update(method="pdf_page_text_match", page=page,
                             verified=all(normalized(device[field]) in content for field in fields))
                if not check["verified"]:
                    check["reason"] = "Hersteller, Modell und Seriennummer nicht gemeinsam auf der angegebenen Seite gefunden."
            except ImportError:
                check["reason"] = "pypdf fehlt; Projekt-Requirements installieren."
            except Exception:
                check["reason"] = "PDF-Seite nicht lesbar; Beleg lokal prüfen."
        else:
            review = evidence.get("identity_review", {})
            check.update(method="visual_label_review", verified=(
                review.get("method") == "visual_label_review"
                and review.get("sha256") == digest and bool(review.get("reviewed_at"))
                and all(review.get(field) == device[field] for field in fields)))
            if not check["verified"]:
                check["reason"] = "Bildbeleg benötigt eine dokumentierte Sichtprüfung mit passendem Dateihash."
        checks.append(check)
    verified = any(check["verified"] for check in checks)
    return verified, checks, [] if verified else ["Geräteidentität ist durch die angegebenen Belege noch nicht vollständig geprüft."]


def asset_candidates(device, register):
    candidates = []
    for row in register["rows"]:
        description = row["description"]
        reasons = []
        if text(device.get("serial_number")) and len(normalized(device["serial_number"])) >= 5:
            if normalized(device["serial_number"]) in normalized(description):
                reasons.append("Seriennummer im Beschreibungstext")
        model = normalized(device.get("model"))
        if len(model) >= 7 and model in normalized(description):
            reasons.append("gleicher Modelltext; allein keine Gerätezuordnung")
        if device.get("kind") == "mfc" and re.search(r"mass[ae]n?durchflussregler", description, re.I):
            value = device.get("range_max")
            if isinstance(value, (int, float)) and re.search(rf"\b{re.escape(f'{value:g}')}(?:[,.]0+)?\s*m[Ll]/min", description):
                reasons.append("gleiche numerische Bereichsangabe; Bezugsbedingungen nicht belegt")
        if reasons:
            candidates.append({**row, "reasons": reasons, "assignment_confirmed": False})
    return candidates


def build_assignment_report(root=ROOT):
    root = Path(root).resolve()
    setup_path = root / "config/gasi_setup.json"
    if not setup_path.is_file():
        return dict(available=False, message="config/gasi_setup.json fehlt; aktuelles Setup zuerst lokal eintragen.", rows=[])
    raw = setup_path.read_bytes()
    setup = json.loads(raw)
    if setup.get("scope") != "current_only" or not isinstance(setup.get("devices"), list):
        raise ValueError("Gerätezuordnung benötigt den aktuellen Stand mit scope=current_only und devices.")
    private = (root / "data/datasheets").resolve()
    if setup.get("inventory_source"):
        register_path = (root / setup["inventory_source"]).resolve()
        if not register_path.is_relative_to(private):
            raise ValueError("Inventarquelle muss unter data/datasheets liegen.")
    else:
        sources = list(private.glob("*Inventar.csv"))
        register_path = sources[0] if len(sources) == 1 else None
    register = read_register(register_path) if register_path is not None and register_path.is_file() else dict(
        rows=[], source=str(register_path) if register_path else None, sha256=None,
        issue="Inventarquelle fehlt oder ist mehrdeutig; inventory_source in der lokalen Setup-Datei setzen.")
    rows, cache, seen = [], {}, {}
    for device in setup["devices"]:
        verified, checks, issues = verify_identity(device, root, cache)
        key = identity_key(device)
        row = dict(position=device["position"], manufacturer=device.get("manufacturer"), model=device.get("model"),
                   serial_number=device.get("serial_number"), kind=device.get("kind"), identity_key=key,
                   suggested_code=device_code(device), identity_verified=verified, evidence=checks, issues=issues,
                   installed_confirmed=device.get("installed_confirmed") is True,
                   calibration_status=device.get("calibration_status", "not_assessed"),
                   open_issues=list(device.get("open_issues", [])), asset_candidates=asset_candidates(device, register),
                   inventory_number=None, openbis_identifier=device.get("openbis_identifier"))
        if row["openbis_identifier"]:
            row["openbis"] = dict(identifier=row["openbis_identifier"], permId=device.get("openbis_perm_id"),
                                  url=device.get("openbis_url"))
        assignment = device.get("inventory_assignment", {})
        if assignment.get("confirmed") is True:
            number = assignment.get("number")
            if not assignment.get("evidence") or number not in {r["number"] for r in register["rows"]}:
                row["issues"].append("Bestätigte Inventarnummer ohne passenden CSV-Eintrag oder Zuordnungsbeleg.")
                row["identity_verified"] = False
            else:
                row["inventory_number"] = number
        if key:
            if key in seen:
                for item in (row, seen[key]):
                    item["identity_verified"] = False
                    item["issues"].append("Dieselbe Geräteidentität ist mehreren Positionen zugeordnet; zunächst klären.")
            else:
                seen[key] = row
        rows.append(row)
    return dict(available=True, setup_id=setup.get("setup_id"), source=str(setup_path), setup_sha256=sha256(raw).hexdigest(),
                register={key: value for key, value in register.items() if key != "rows"},
                register_rows=len(register["rows"]), rows=rows,
                checked_at=datetime.now(timezone.utc).isoformat(),
                message="Geräteidentität, Anlagen-Inventarnummer und aktueller Einbau getrennt geprüft; keine Registrierung.")


def write_assignment_report(report, directory=REPORT_DIRECTORY):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, html_path = (directory / (REPORT_NAME + suffix) for suffix in (".json", ".html"))
    if json_path.resolve() == Path(report.get("source", "")).resolve():
        raise ValueError("Der Bericht darf seine Quelldatei nicht überschreiben.")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    body = []
    for row in report["rows"]:
        candidates = row["asset_candidates"]
        assets = ("bestätigt: " + escape(row["inventory_number"])) if row["inventory_number"] else "Zuordnung offen"
        if candidates:
            assets += f'<details><summary>{len(candidates)} Kandidaten</summary>' + "".join(
                f'<p>{escape(item["number"])} · {escape("; ".join(item["reasons"]))}<br>{escape(item["description"])}</p>'
                for item in candidates) + "</details>"
        issues = row["issues"] + row["open_issues"]
        status = "Identität belegt" if row["identity_verified"] else "Identität offen"
        status += "<br>Einbau: " + ("bestätigt" if row["installed_confirmed"] else "offen")
        if row.get("registration_status"):
            statuses = dict(identity_open="Identität offen", location_open="Standort offen",
                            conflict="Bestandskonflikt", schema_open="Typ/Pflichtfeld offen",
                            create="bereit zur Anlage", created="angelegt", reuse="Bestand wiederverwendet")
            status += "<br>Inventar: " + escape(statuses[row["registration_status"]])
            if row.get("registration_reason"):
                status += "<br>" + escape(row["registration_reason"])
        if issues:
            status += '<details><summary>Offene Angaben</summary>' + "".join(f"<p>{escape(i)}</p>" for i in issues) + "</details>"
        proof = "<br>".join(escape(Path(e["file"]).name) + (f' · S. {e["page"]}' if e.get("page") else "") for e in row["evidence"] if e["verified"]) or "offen"
        remote = row.get("openbis", {})
        link = remote.get("url")
        if link:
            parsed = urlsplit(link)
            if parsed.scheme != "https" or parsed.netloc != "playground.datastore.bam.de":
                link = None
        identifier = remote.get("identifier") or row.get("openbis_identifier") or "noch nicht angelegt"
        remote_html = f'<a href="{escape(link, quote=True)}">{escape(identifier)}</a>' if link else escape(identifier)
        body.append(f'<tr><td>{escape(row["position"])}</td><td>{escape(text(row["manufacturer"]))}<br>{escape(text(row["model"]))}<br><b>{escape(text(row["serial_number"])) or "Seriennummer offen"}</b></td><td>{assets}</td><td>{proof}</td><td>{status}</td><td>{remote_html}</td></tr>')
    document = '<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GaSi Gerätezuordnung</title><style>body{font:16px/1.5 system-ui,sans-serif;color:#183448;max-width:1450px;margin:24px auto;padding:0 18px}h1{font-size:1.8rem}.note{background:#fff5dc;padding:12px}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.87rem}td,th{border:1px solid #ccd9df;padding:10px;text-align:left;vertical-align:top}th{background:#eef5f7}summary{cursor:pointer}td{overflow-wrap:anywhere}details p{max-width:55ch}a{color:#126b88}</style><h1>GaSi: Geräte zuordnen</h1><p class="note">Nur lokal. Ein Modelltreffer bestätigt keine Inventarnummer. Ein Gerätebeleg bestätigt keinen aktuellen Einbau und keine Kalibriergültigkeit.</p>'
    document += f'<p>{len(report["rows"])} Positionen · {sum(r["identity_verified"] for r in report["rows"])} belegte Identitäten · {report.get("register_rows", 0)} Einträge in der Inventarquelle</p>'
    if report.get("location"):
        location = report["location"]
        document += '<p><b>Gemeldeter Standort:</b> ' + escape(text(location.get("reported_text")) or "noch nicht bestätigt")
        document += '<br><b>BAM-Wert:</b> ' + escape(text(location.get("label")) or text(location.get("code")) or "offen") + '</p>'
        if location.get("mapping_note"):
            document += '<p class="note">' + escape(location["mapping_note"]) + '</p>'
    document += '<div class="table"><table><tr><th>Position</th><th>Gerät / Seriennummer</th><th>Anlagen-Inventarnummer</th><th>Beleg</th><th>Prüfstand</th><th>openBIS</th></tr>' + "".join(body) + "</table></div></html>"
    html_path.write_text(document, encoding="utf-8")
    return html_path


def show_assignment_summary(report):
    print(report["message"])
    if report["available"]:
        print(f'Positionen: {len(report["rows"])}; belegte Identitäten: {sum(r["identity_verified"] for r in report["rows"])}; bestätigte Anlagen-Inventarnummern: {sum(bool(r["inventory_number"]) for r in report["rows"])}.')
        print("Seriennummern, Belege, Inventarkandidaten und offene Zuordnungen stehen nur im lokalen Bericht.")
