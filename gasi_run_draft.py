"""Local guided run preparation. Opening/saving the form never contacts openBIS."""
from copy import deepcopy
import csv
from datetime import datetime
from html import escape
import io
import json
from pathlib import Path
import re
import tempfile

import gasi_run as runs
import gasi_openbis_playground as ob
from gasi_inventory_openbis import _atomic_json
from gasi_local_measurements import inspect_measurements, NUMERIC_FIELDS

ROOT = Path(__file__).resolve().parent


def readable_issue(message):
    labels = {
        "Pflichtangabe fehlt: run_id.": "Laufkennung fehlt; Prüfling und Dateien auswählen oder eine Kennung eintragen.",
        "Pflichtangabe fehlt: purpose.": "Prüfzweck eintragen.",
        "Pflichtangabe fehlt: responsible_person.": "Verantwortliche Person eintragen.",
        "Identität und vorhandene openBIS-ID des Sensor-Prüflings bestätigen.": "Den tatsächlich verwendeten Prüfling auswählen (openBIS-ID).",
        "Bestätigung mit Beleg fehlt: source_association_confirmed.": "Dateien und Messbereich diesem Lauf zuordnen.",
        "Explizite Dateien fehlen: raw_data.": "Mindestens eine Originaldatei auswählen.",
        "Pilot: eindeutige Dateizuordnung exclusive_run ausdrücklich bestätigen.": "Die Zugehörigkeit der Originale klären: nur dieser Messlauf oder mehrere Läufe?",
        "Jeder ausgewertete Kanal benötigt bestätigte Objekt-, Größen-, Einheiten- und Messortzuordnung.": "Für den gewählten Kanal Größe, Einheit und Messort ergänzen.",
    }
    if message.startswith("Beaufschlagung und Messung: Beginn/Ende"):
        return "Die tatsächliche Zeitbasis für jede ausgewählte Datei festlegen."
    return labels.get(message, message)


def readable_issues(issues, config):
    """Explain the primary missing selection instead of its missing generated run ID."""
    config = config or {}
    ref = (config.get("dut") or {}).get("identifier")
    labels = []
    for issue in issues:
        if issue == "Pflichtangabe fehlt: run_id." and (config.get("measurement_subject", "sensor") == "sensor" and not runs._reference(ref) or not (config.get("files") or {}).get("raw_data")):
            continue
        if issue == "Identität und vorhandene openBIS-ID des Sensor-Prüflings bestätigen.":
            text = ("Prüflingsbezeichnung noch keinem openBIS-Objekt zugeordnet. 'Prüfling suchen' verwenden oder den Sensor im Prüflingsnotebook anlegen."
                    if ref and not runs._reference(ref) else "Prüfling noch nicht ausgewählt. Gültige openBIS-ID übernehmen und den Entwurf speichern.")
        else:
            text = readable_issue(issue)
        if text not in labels:
            labels.append(text)
    return labels


def _load(path, fallback=None):
    if not path.exists():
        return deepcopy(fallback)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (OSError, ValueError):
        raise ob.CheckFailed("Lokale Konfiguration nicht lesbar: " + path.name) from None


def file_choices(root=ROOT):
    root = Path(root).resolve()
    return [p.relative_to(root).as_posix() for p in sorted((root / "data/measurements").glob("*.csv"))
            if p.is_file() and p.resolve().is_relative_to(root / "data/measurements")]


def source_summary(root, name, first=1, last=None):
    """Reuse the CSV validator; records exclude repeated headers, matching upload/analysis."""
    root = Path(root).resolve()
    path = runs._source(root, name)
    if path.suffix.lower() != ".csv" or not path.is_relative_to(root / "data/measurements"):
        raise ob.CheckFailed("Originale ausschließlich aus data/measurements auswählen.")
    raw = path.read_bytes()
    scratch = root / ".local_playground_test"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="draft-check-", dir=scratch) as temp:
        folder = Path(temp)
        (folder / path.name).write_bytes(raw)
        try:
            checked = inspect_measurements(folder, folder / "preview.json")
        except ValueError:
            raise ob.CheckFailed("CSV besteht die Zeilen-, Zahlen- oder Zeitprüfung nicht: " + path.name) from None
    count = checked["rows_checked"]
    last = count if last is None else last
    if not runs._record(first) or not runs._record(last) or not 1 <= first <= last <= count:
        raise ob.CheckFailed("Datenbereich liegt außerhalb der Datei: " + path.name)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t")
    headers = tuple(reader.fieldnames)
    start = end = previous = None
    observed, segments, numeric = {}, [], set()
    signature = None
    number = 0
    for row in reader:
        if tuple(row.get(k) for k in headers) == headers:
            continue
        number += 1
        if not first <= number <= last:
            continue
        stamp = datetime.strptime(row["Datum"] + " " + row["Uhrzeit"], "%d.%m.%Y %H:%M:%S")
        if previous is not None and stamp < previous:
            raise ob.CheckFailed("Zeit springt im ausgewählten Bereich zurück; Bereich/Zeitbasis klären.")
        start = start or stamp
        end = previous = stamp
        numeric.update(k for k in NUMERIC_FIELDS if row.get(k, "").strip())
        current = tuple(row.get(k, "") for k in ("GASPROFIL_ID", "AUTOMATIK_STATUS"))
        if current != signature:
            if segments:
                segments[-1]["last_record"] = number - 1
            segments.append(dict(first_record=number, last_record=number, gas_profile=current[0], logger_status=current[1]))
            signature = current
        else:
            segments[-1]["last_record"] = number
        for key, value in row.items():
            if value and (key in ("PROJEKT_NAME", "GASPROFIL_ID", "GASPROFIL_NAME_DE", "AUTOMATIK_STATUS", "GESAMTFLOW_SOLL") or
                          re.fullmatch(r"K[1-3]_(GAS_ID|KONZENTRATION|EINHEIT)", key)):
                values = observed.setdefault(key, set())
                if len(values) < 12:
                    values.add(value)
    return dict(file=name, sha256=runs._hash(raw), records=count, first_record=first, last_record=last,
                first_local=start.isoformat(), last_local=end.isoformat(), numeric_columns=sorted(numeric),
                observed_values={k: sorted(v) for k, v in observed.items()},
                logger_segments=segments[:100], logger_segment_count=len(segments))


def build_draft(*, root=ROOT, selections, dut_id, purpose, responsible_person, run_id="", dut_kind="gas_humidity_sensor",
                instruments=(), ownership="unknown", setup_evidence="", signal=None, acquisition_version="", base=None,
                measurement_subject="sensor", subject_evidence=""):
    """Explicit user choices become the factual record; unknown conditions remain unknown."""
    root = Path(root).resolve()
    template = _load(root / "config/gasi_run.example.json")
    if template is None:
        raise ob.CheckFailed("Laufvorlage fehlt.")
    data = {**deepcopy(template), **deepcopy(base or {})}
    source_details = []
    seen = set()
    for selection in selections:
        if selection["file"] in seen:
            raise ob.CheckFailed("Datei nur einmal auswählen; Datenbereich pro Datei festlegen.")
        seen.add(selection["file"])
        summary = source_summary(root, selection["file"], selection.get("first_record", 1), selection.get("last_record"))
        if selection.get("sha256") and selection["sha256"] != summary["sha256"]:
            raise ob.CheckFailed("Original seit der Auswahl verändert; Dateien erneut laden.")
        source_details.append(summary)
    ranges = [{"file": s["file"], "first_record": d["first_record"], "last_record": d["last_record"],
               "utc_offset": s.get("utc_offset") or None, "confirmed": True}
              for s, d in zip(selections, source_details)]
    sensor = measurement_subject == "sensor"
    if not run_id.strip() and source_details and (not sensor or runs._reference(dut_id.strip())):
        identity = {**({"dut": dut_id.strip()} if sensor else {"measurement_subject":measurement_subject}), "sources": sorted(
            [{"sha256": d["sha256"], "first": d["first_record"], "last": d["last_record"]} for d in source_details], key=lambda d: json.dumps(d))}
        run_id = "GASI_" + source_details[0]["first_local"][:10].replace("-", "") + "_" + runs._hash(runs._json(identity))[:12].upper()
    starts, ends = [], []
    for area, detail in zip(ranges, source_details):
        zone = runs._offset(area["utc_offset"])
        if zone is not None:
            starts.append(datetime.fromisoformat(detail["first_local"]).replace(tzinfo=zone))
            ends.append(datetime.fromisoformat(detail["last_local"]).replace(tzinfo=zone))
    times = dict(start=min(starts).isoformat(), end=max(ends).isoformat()) if ranges and len(starts) == len(ranges) else dict(start=None, end=None)
    setup = _load(root / "config/gasi_setup.json", {})
    used = [d for d in setup.get("devices", []) if d.get("openbis_identifier") in instruments]
    snapshot = dict(setup_id=setup.get("setup_id"),
                    configuration_sha256=runs._hash((root / "config/gasi_setup.json").read_bytes()) if setup else None,
                    used_devices=[{k: d.get(k) for k in ("position", "openbis_identifier", "quantity", "unit",
                                  "reference_temperature_C", "reference_pressure_hPa_abs")} for d in used],
                    applies_to_this_run=bool(setup_evidence.strip()))
    channels = []
    if sensor and signal and signal.get("column"):
        channels = [{**signal, "role": "dut_signal", "object_identifier": dut_id.strip(), "confirmed": True}]
    data.update(metadata_profile="raw_capture", upload_scope="measurement", run_id=run_id.strip() or None, purpose=purpose.strip() or None,
                responsible_person=responsible_person.strip() or None,
                dut=dict(identifier=dut_id.strip() or None if sensor else None, kind=dut_kind if sensor else None,
                         identity_confirmed=sensor and runs._reference(dut_id.strip())),
                resources=dict(instruments=list(instruments), gas_sources=[], sop=[], software=[]),
                stages=[], channels=channels, stage_ranges=[], source_ranges=ranges,
                source_file_sha256={s["file"]: s["sha256"] for s in source_details},
                files=dict(preparation=[], raw_data=[s["file"] for s in source_details]),
                times=dict(measurement=times), software_versions=dict(acquisition=acquisition_version.strip() or None),
                setup_confirmed=bool(setup_evidence.strip()), setup_evidence=setup_evidence.strip() or None,
                setup_snapshot=snapshot, source_association_confirmed=bool(ranges),
                source_association_evidence="Dateien und Record-Bereiche im lokalen Formular diesem Lauf zugeordnet." if ranges else None,
                raw_file_policy=dict(mode="exclusive_run", confirmed=ownership == "exclusive",
                    evidence="Im Formular als ausschließlich diesem Lauf zugehörig angegeben." if ownership == "exclusive" else None,
                    shared_sources=[dict(file=s["file"], run_ids=[run_id] if run_id else []) for s in source_details] if ownership == "shared" else []),
                draft_provenance=dict(source="GaSi_03_Messdaten_hochladen.ipynb", source_observations=source_details,
                    interpretation="CSV-Profile und Logabschnitte sind Vorschläge, keine bestätigten Messstufen."))
    if measurement_subject != "sensor" or base and "measurement_subject" in base:
        data.update(measurement_subject=measurement_subject, subject_evidence=subject_evidence.strip() or
                    {"system":"Als Anlagenlauf ohne externen Sensor angegeben.",
                     "unresolved":"Prüflingsbezug noch ungeklärt."}.get(measurement_subject))
    # Retain an already described run only when its source/record/DUT association is unchanged.
    old_ref = (base or {}).get("dut", {}).get("identifier")
    same_binding = base and (old_ref == data["dut"]["identifier"] or not sensor and not runs._reference(old_ref)) and base.get("source_ranges") == ranges
    if same_binding:
        if (base.get("setup_evidence") == data["setup_evidence"] and
                set(base.get("resources", {}).get("instruments", [])) == set(instruments)):
            # A later edit of the global setup must not silently rewrite the recorded snapshot.
            data["setup_snapshot"] = deepcopy(base.get("setup_snapshot"))
        for key in ("stages", "stage_ranges", "reference_assessment", "reference_evidence", "preparation"):
            data[key] = deepcopy(base.get(key, data.get(key)))
        data["resources"]["gas_sources"] = deepcopy(base.get("resources", {}).get("gas_sources", []))
        for key in ("sop", "software"):
            data["resources"][key] = deepcopy(base.get("resources", {}).get(key, []))
        data["files"]["preparation"] = deepcopy(base.get("files", {}).get("preparation", []))
        owners = {dut_id.strip(), *instruments, *data["resources"]["gas_sources"], *data["resources"]["sop"]}
        data["channels"] += [deepcopy(c) for c in base.get("channels", []) if c.get("role") != "dut_signal" and c.get("object_identifier") in owners]
        if sensor and base.get("metadata_profile") != "raw_capture" and not runs.validate_run(base, root):
            data["metadata_profile"] = "described_run"
            data["times"] = {k: deepcopy(v) for k, v in base["times"].items() if k != "analysis"}
    data["metadata_gaps"] = runs.metadata_gaps(data)
    return dict(config=data, issues=runs.validate_run(data, root), metadata_gaps=data["metadata_gaps"])


def config_hash(root=ROOT):
    path = Path(root) / "config/gasi_run.json"
    return runs._hash(path.read_bytes()) if path.exists() else None


def save_draft(draft, *, root=ROOT, expected_hash):
    """Save locally, retain the previous version, and reject concurrent edits."""
    root = Path(root)
    if config_hash(root) != expected_hash:
        raise ob.CheckFailed("Laufkonfiguration inzwischen geändert; Formular neu öffnen, damit nichts überschrieben wird.")
    path = root / "config/gasi_run.json"
    if path.exists():
        backup = root / ".local_playground_test/run_drafts" / expected_hash / "gasi_run.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    _atomic_json(path, draft["config"], ".gasi-setup-")
    return config_hash(root)


class RunPreparation:
    """Small widget controller, kept outside the notebook; callbacks expose no credentials."""
    def __init__(self, root=ROOT):
        import ipywidgets as w
        self.w, self.root = w, Path(root).resolve()
        self.base = _load(self.root / "config/gasi_run.json", {})
        self.expected_hash = config_hash(self.root)
        self.result, self.message = None, "Noch keine Messung ausgeführt."
        self.file_rows = {}
        setup = _load(self.root / "config/gasi_setup.json", {})
        dut = _load(self.root / "config/gasi_pruefling.json", {})
        style = dict(description_width="160px")
        layout = w.Layout(width="100%")
        def text(label, value="", placeholder=""):
            return w.Text(description=label, value=value or "", placeholder=placeholder, style=style, layout=layout)
        self.files = w.SelectMultiple(options=file_choices(self.root), description="Originaldateien", rows=7, style=style, layout=layout)
        self.purpose = text("Prüfzweck", self.base.get("purpose"), "Was wurde mit GaSi oder dem Sensor untersucht?")
        self.person = text("Verantwortliche Person", self.base.get("responsible_person"))
        self.run_id = text("Laufkennung", self.base.get("run_id"), "Leer lassen: aus ausgewählten Daten und Laufart erzeugen")
        self.subject = w.Dropdown(options=[("Sensorprüfung", "sensor"), ("Anlagenlauf ohne externen Prüfling", "system"),
                    ("Prüflingsbezug noch ungeklärt", "unresolved")], value=self.base.get("measurement_subject", "sensor"),
                    description="Art der Aufzeichnung", style=style, layout=layout)
        self.subject_note = text("Hinweis zur Laufart", self.base.get("subject_evidence"), "Optional: Grundlage oder noch bestehende Unsicherheit")
        self.dut = text("Prüfling: ID oder Suche", self.base.get("dut", {}).get("identifier") or dut.get("identifier"), "Name/Code eingeben und suchen oder vollständige openBIS-ID einsetzen")
        self.search_button = w.Button(description="Prüfling suchen (lesend)", layout=w.Layout(width="210px"))
        self.dut_matches = w.Dropdown(options=[("Noch kein Prüfling aus der Suche übernommen", "")],
                                     description="Gefundene Prüflinge", style=style, layout=layout)
        self.dut_matches.observe(self._pick_dut, names="value")
        self.kind = w.Dropdown(options=[("Gasfeuchtesensor", "gas_humidity_sensor"), ("Gassensor", "gas_sensor")],
                               value=self.base.get("dut", {}).get("kind") or "gas_humidity_sensor", description="Sensorart", style=style)
        choices = [(str(d.get("position")) + " · " + str(d.get("model") or "Gerät"), d["openbis_identifier"])
                   for d in setup.get("devices", []) if d.get("openbis_identifier")]
        known = {v for _, v in choices}
        choices += [("Bisher verwendetes Gerät · " + v, v) for v in self.base.get("resources", {}).get("instruments", []) if v not in known]
        self.devices = w.SelectMultiple(options=choices, description="Beteiligte Geräte", rows=min(7, max(2, len(choices))), style=style, layout=layout)
        self.devices.value = tuple(v for v in self.base.get("resources", {}).get("instruments", []) if v in {v for _, v in choices})
        self.setup_evidence = text("Aufbauzuordnung", self.base.get("setup_evidence"), "Optional: z. B. Aufbau laut Messprotokoll vom …")
        self.version = text("Aufnahmesoftware", self.base.get("software_versions", {}).get("acquisition"), "Unbekannt darf offen bleiben")
        self.ownership = w.Dropdown(options=[("Noch ungeklärt", "unknown"), ("Nur dieser Messlauf", "exclusive"),
                                  ("Auch andere Messläufe", "shared")], description="Originale gehören zu", style=style, layout=layout)
        policy = self.base.get("raw_file_policy") or {}
        self.ownership.value = "shared" if policy.get("shared_sources") else "exclusive" if policy.get("confirmed") else "unknown"
        self.signal = w.Dropdown(options=[("Noch nicht zugeordnet", "")], description="Prüflingskanal", style=style, layout=layout)
        self.quantity = text("Signalgröße", placeholder="z. B. voltage")
        self.unit = text("Signaleinheit", placeholder="z. B. mV")
        self.location = text("Signal-Messort", placeholder="z. B. elektrischer Sensorausgang")
        self.signal.observe(self._signal_changed, names="value")
        self.ranges = w.VBox()
        self.summary = w.HTML()
        self.output = w.Output()
        self.status = w.HTML()
        self.load_button = w.Button(description="Dateiauswahl einlesen", layout=w.Layout(width="210px"))
        self.save_button = w.Button(description="Entwurf lokal speichern", button_style="info", layout=w.Layout(width="210px"))
        self.execute_button = w.Button(description="Messung ausführen", button_style="primary", layout=w.Layout(width="210px"))
        self.new_button = w.Button(description="Neuen Lauf vorbereiten", layout=w.Layout(width="210px"))
        self.load_button.on_click(lambda _: self._callback(self.load_sources))
        self.save_button.on_click(lambda _: self._callback(self.save))
        self.execute_button.on_click(lambda _: self._callback(self.execute))
        self.new_button.on_click(lambda _: self._callback(self.new_run))
        self.search_button.on_click(lambda _: self._callback(self.search_dut))
        extra = w.Accordion(children=[w.VBox([self.devices, self.setup_evidence, self.version,
                     self.signal, self.quantity, self.unit, self.location])], titles=("Aufbau und Signalkanal zuordnen – offene Angaben sind möglich",))
        extra.selected_index = None
        self.widget = w.VBox([w.HTML("<h3>1 · Originale und Datenbereich wählen</h3>"), self.files, self.load_button,
            self.ranges, self.summary, self.ownership, w.HTML("<h3>2 · Messlauf beschreiben</h3>"),
            self.subject, self.subject_note, self.dut, self.search_button, self.dut_matches, self.kind, self.purpose, self.person, self.run_id, extra,
            w.HTML("<p>Speichern ordnet die gewählten Records diesem Lauf zu. Unbekannte Messbedingungen bleiben offen. "
                   "Die Zeitbasis und die Zugehörigkeit der Originale müssen für den Upload geklärt sein.</p>"),
            self.status, w.HBox([self.new_button, self.save_button, self.execute_button]), self.output])
        existing = tuple(v for v in self.base.get("files", {}).get("raw_data", []) if v in self.files.options)
        self.files.value = existing
        if existing:
            self.load_sources()
        self.saved_state = self._state()
        self.subject.observe(self._subject_changed, names="value")
        self._subject_changed(None)
        for field in (self.files, self.subject, self.subject_note, self.dut, self.kind, self.purpose, self.person, self.run_id, self.devices,
                      self.ownership, self.setup_evidence, self.version, self.signal, self.quantity, self.unit, self.location):
            field.observe(lambda _: self._refresh_status(), names="value")
        self._refresh_status()

    def _callback(self, action):
        with self.output:
            self.output.clear_output()
            try:
                action()
            except ob.CheckFailed as exc:
                print(str(exc))
            except Exception:
                print("Vorbereitung unvollständig; Dateien, lokale Konfiguration und Eingaben prüfen. Details bleiben lokal.")
            finally:
                self._refresh_status()

    def _refresh_status(self):
        if not hasattr(self, "saved_state"):
            return
        if config_hash(self.root) != self.expected_hash:
            self.status.value = '<p><b>Laufkonfiguration außerhalb dieses Formulars geändert.</b> Formularzelle erneut ausführen, um die gespeicherten Angaben zu laden.</p>'
            return
        if self._state() == self.saved_state and not (self.base.get("files") or {}).get("raw_data"):
            self.status.value = '<p><b>Noch kein Messlauf vorbereitet.</b> Originale auswählen, Laufart beschreiben und den Entwurf lokal speichern.</p>'
            return
        if self._state() != self.saved_state:
            text = "Eingaben noch nicht gespeichert. Entwurf lokal speichern; danach die angezeigten offenen Punkte prüfen."
            color = "#805600"
        else:
            issues = readable_issues(runs.validate_run(self.base, self.root), self.base)
            if issues:
                text = "Noch nicht uploadbereit:<ul>" + "".join("<li>" + escape(v) + "</li>" for v in issues) + "</ul>"
                self.status.value = '<div style="border-left:4px solid #a32b20;padding:8px 12px">' + text + '</div>'
                return
            text, color = "Entwurf gespeichert; lokale Mindestangaben vorhanden. Offene Fachangaben bleiben gekennzeichnet. Messung ausführen verwendet den Sessionmodus.", "#216239"
        self.status.value = '<div style="border-left:4px solid ' + color + ';padding:8px 12px">' + escape(text) + '</div>'

    def _pick_dut(self, change):
        if change["new"]:
            self.dut.value = change["new"]

    def _subject_changed(self, change):
        enabled = self.subject.value == "sensor"
        for field in (self.dut, self.search_button, self.dut_matches, self.kind, self.signal, self.quantity, self.unit, self.location):
            field.disabled = not enabled

    def search_dut(self):
        import gasi_dut
        matches, message = gasi_dut.find_duts(self.dut.value)
        self.dut_matches.options = [("Passenden Eintrag auswählen", "")] + [
            (m["name"] + " · " + m["identifier"], m["identifier"]) for m in matches]
        if len(matches) == 1:
            self.dut_matches.value = matches[0]["identifier"]
        print(message)
        return matches

    def _signal_changed(self, change):
        if change["new"].endswith("_mV"):
            self.quantity.value, self.unit.value = "voltage", "mV"
        elif not change["new"]:
            self.quantity.value = self.unit.value = self.location.value = ""

    def load_sources(self):
        self.file_rows = {}
        rows, columns, descriptions = [], None, []
        old_ranges = {s["file"]: s for s in self.base.get("source_ranges", [])}
        for name in self.files.value:
            detail = source_summary(self.root, name)
            old = old_ranges.get(name, {})
            first = self.w.BoundedIntText(value=old.get("first_record", 1), min=1, max=detail["records"], description="Erster Record")
            last = self.w.BoundedIntText(value=old.get("last_record", detail["records"]), min=1, max=detail["records"], description="Letzter Record")
            options = [("Unbekannt", ""), ("UTC", "Z"), ("MEZ (UTC+01:00)", "+01:00"), ("MESZ (UTC+02:00)", "+02:00")]
            offset = old.get("utc_offset") or ""
            if offset not in {v for _, v in options}:
                options.append((offset, offset))
            zone = self.w.Dropdown(options=options, value=offset, description="Zeitbasis")
            self.file_rows[name] = dict(detail=detail, first=first, last=last, offset=zone)
            for field in (first, last, zone):
                field.observe(lambda _: self._refresh_status(), names="value")
            rows.append(self.w.VBox([self.w.HTML("<b>" + escape(name) + "</b> · " + str(detail["records"]) + " Records"),
                                    self.w.HBox([first, last, zone])]))
            available = set(detail["numeric_columns"])
            columns = available if columns is None else columns & available
            descriptions.append(escape(name) + ": " + escape(detail["first_local"]) + " bis " + escape(detail["last_local"]) +
                                " (lokale Loggerzeit); " + str(detail["logger_segment_count"]) + " Logabschnitte als Vorschlag.")
            observations = "<br>".join(escape(k) + ": " + escape(", ".join(v)) for k, v in detail["observed_values"].items())
            if observations:
                descriptions.append("<details><summary>Übernommene CSV-Angaben ansehen</summary>" + observations +
                                    "<p>Loggerwerte und Sollprofile; kein Nachweis der tatsächlich am Sensor anliegenden Bedingungen.</p></details>")
        self.ranges.children = rows
        self.summary.value = "<div>" + "<br>".join(descriptions or ["Keine Datei ausgewählt. Originaldateien bleiben unverändert."]) + "</div>"
        self.signal.options = [("Noch nicht zugeordnet", "")] + [(v, v) for v in sorted(columns or ())]
        old_signal = next((c for c in self.base.get("channels", []) if c.get("role") == "dut_signal"), {})
        if old_signal.get("column") in (columns or set()):
            self.signal.value = old_signal["column"]
            self.quantity.value, self.unit.value, self.location.value = (old_signal.get(k, "") for k in ("quantity", "unit", "location"))

    def _state(self):
        return dict(files=list(self.files.value), ranges=[dict(file=n, first=r["first"].value, last=r["last"].value,
                    offset=r["offset"].value) for n, r in self.file_rows.items()], purpose=self.purpose.value,
                    person=self.person.value, run_id=self.run_id.value, dut=self.dut.value, kind=self.kind.value,
                    subject=self.subject.value, subject_note=self.subject_note.value,
                    instruments=list(self.devices.value), ownership=self.ownership.value, setup=self.setup_evidence.value,
                    version=self.version.value, signal=self.signal.value, quantity=self.quantity.value,
                    unit=self.unit.value, location=self.location.value)

    def save(self):
        if set(self.files.value) != set(self.file_rows):
            raise ob.CheckFailed("Geänderte Dateiauswahl zuerst einlesen.")
        selections = [dict(file=n, first_record=r["first"].value, last_record=r["last"].value,
                           utc_offset=r["offset"].value, sha256=r["detail"]["sha256"]) for n, r in self.file_rows.items()]
        signal = dict(column=self.signal.value, quantity=self.quantity.value, unit=self.unit.value, location=self.location.value) if self.signal.value else None
        draft = build_draft(root=self.root, selections=selections, dut_id=self.dut.value, purpose=self.purpose.value,
                  responsible_person=self.person.value, run_id=self.run_id.value, dut_kind=self.kind.value,
                  instruments=self.devices.value, ownership=self.ownership.value, setup_evidence=self.setup_evidence.value,
                  signal=signal, acquisition_version=self.version.value, base=self.base,
                  measurement_subject=self.subject.value, subject_evidence=self.subject_note.value)
        self.expected_hash = save_draft(draft, root=self.root, expected_hash=self.expected_hash)
        self.base = draft["config"]
        self.run_id.value = self.base["run_id"] or ""
        self.saved_state = self._state()
        print("Entwurf lokal gespeichert. Keine openBIS-Abfrage, kein Upload.")
        if draft["issues"]:
            print("Vor dem Upload ergänzen:")
        for message in readable_issues(draft["issues"], self.base):
            print("-", message)
        if draft["metadata_gaps"]:
            print("Als offen dokumentiert:")
        for message in draft["metadata_gaps"]:
            print("-", message)
        if not draft["issues"]:
            print("Lokale Angaben bereit. Messung ausführen verwendet den zentralen Sessionmodus.")
        self._refresh_status()
        return draft

    def execute(self):
        if self._state() != self.saved_state or config_hash(self.root) != self.expected_hash:
            raise ob.CheckFailed("Eingaben geändert; Entwurf vor der Ausführung lokal speichern oder Formular neu öffnen.")
        import gasi_workflow as app
        self.result, self.message = app.upload_measurement(self.root)
        shown = {**self.result, "issues": readable_issues(self.result.get("issues", []), self.base)}
        app.show_result(shown, self.message)
        self._refresh_status()
        return self.result, self.message

    def new_run(self):
        self.base = {}
        self.run_id.value = self.purpose.value = ""
        self.files.value = ()
        self.load_sources()
        self.ownership.value = "unknown"
        self.devices.value = ()
        self.setup_evidence.value = self.version.value = ""
        self.subject_note.value = ""
        self.saved_state = None
        print("Neuer Lauf vorbereitet. Vorherige Konfiguration bleibt bis zum Speichern erhalten und wird dabei gesichert.")


def show_run_preparation(root=ROOT):
    from IPython.display import display
    import gasi_session
    print(gasi_session.mode_status())
    print("Lokal verfügbare CSV-Dateien:", len(file_choices(root)))
    try:
        editor = RunPreparation(root)
    except ob.CheckFailed as exc:
        print(str(exc))
        return None
    display(editor.widget)
    return editor
