"""Offline inspection of GaSi measurement exports using only the standard library."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


# Numeric channels inspected or exposed in the local preview. Text IDs/units and
# JSON payloads must never be interpreted as numbers just because of a default 0.
NUMERIC_FIELDS = (
    *(f"K{i}_KONZENTRATION" for i in range(1, 4)),
    *(f"MFC{i}_{suffix}" for i in range(1, 9) for suffix in (
        "ONLINE", "FAKTOR", "FLUIDAT_CF", "INV_CF",
        "SOLL", "SOLL_CO2EQ", "IST", "IST_CO2EQ", "TEMP_C")),
    *(f"MBW{device}_{suffix}" for device in ("373", "473SP2") for suffix in (
        "ONLINE", "FROST_POINT_C", "HEAD_PRESSURE_PA", "EXTERNAL_TEMP_C", "FLOW_L_MIN", "STABLE")),
    "ELP9_SOLL_bar", "ELP9_IST_bar", "ELP9_TEMP_C", "ALICAT_MASS_FLOW",
    "ALICAT_VOLUMETRIC_FLOW", "ALICAT_DRUCK", "ALICAT_TEMP_C", "GESAMTFLOW_SOLL", "GESAMTFLOW_IST",
    "KELLER_P1_bar", "KELLER_P2_bar", "KELLER_T1_C", "KELLER_T2_C",
    "PT_PROZESS_C", "MGK_INPUT_C", "MGK_TSAT_C", "KLIKA_C",
    *(f"A5B_CH{i:02d}_mV" for i in range(1, 17)),
)


def _number_or_none(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = float(raw.replace(",", "."))
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def inspect_measurements(measurement_dir: str | Path, preview_path: str | Path, *, setup_context=None) -> dict[str, Any]:
    """Validate local CSVs and write a value-bearing preview only when files exist."""
    measurement_dir = Path(measurement_dir)
    preview_path = Path(preview_path)
    csv_paths = sorted(path for path in measurement_dir.glob("*.csv") if path.is_file())
    if preview_path.resolve() in {path.resolve() for path in csv_paths}:
        raise ValueError("Die Vorschau darf keine Original-CSV überschreiben.")
    if not csv_paths:
        return {
            "files_checked": 0,
            "rows_checked": 0,
            "schema_variants": 0,
            "column_count": None,
            "parse_errors": 0,
            "numeric_errors": 0,
            "row_shape_errors": 0,
            "ambiguous_clock_rollbacks": [],
            "sampling_intervals_seconds": {},
            "project_names": [],
            "gas_profiles": [],
            "component_ids": [],
            "calibration_entries": 0,
            "calibration_payloads_empty": True,
            "preview_path": None,
            "example_file": None,
            "message": "Keine CSV-Messdateien gefunden. Lege Test- oder Messdateien in data/measurements/ ab.",
        }

    summaries = []
    schemas = set()
    project_names = set()
    gas_profiles = set()
    component_ids = set()
    sampling_intervals: Counter[int] = Counter()
    ambiguous_clock_rollbacks = []
    parse_errors = 0
    numeric_errors = 0
    row_shape_errors = 0
    calibration_entries = 0
    calibration_payloads = []
    column_count = None
    blank_columns = []

    for path in csv_paths:
        file_rows = 0
        start_time = None
        end_time = None
        previous_time = None
        file_intervals: Counter[int] = Counter()
        file_projects = set()
        file_profiles = set()
        file_components = set()
        file_mbw373_online = False

        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, delimiter="\t")
            headers = tuple(reader.fieldnames or ())
            if headers[:3] != ("Datum", "Uhrzeit", "") or len(set(headers)) != len(headers):
                raise ValueError(f"Ungültige/mehrdeutige CSV-Kopfzeile: {path.name}")
            missing_fields = set(NUMERIC_FIELDS) - set(headers)
            if missing_fields:
                raise ValueError(f"Ausgewertete Zahlenfelder fehlen in {path.name}: {sorted(missing_fields)}")
            schemas.add(headers)
            column_count = len(headers) if column_count is None else column_count
            blank_columns = [index for index, name in enumerate(headers) if name == ""]

            for row_number, row in enumerate(reader, start=2):
                if tuple(row.get(key) for key in headers) == headers and None not in row:
                    continue
                file_rows += 1
                if None in row or any(value is None for value in row.values()):
                    row_shape_errors += 1
                    continue
                for field in NUMERIC_FIELDS:
                    raw_value = row.get(field)
                    if raw_value and raw_value.strip() and _number_or_none(raw_value) is None:
                        numeric_errors += 1
                try:
                    timestamp = datetime.strptime(
                        f"{row.get('Datum', '')} {row.get('Uhrzeit', '')}",
                        "%d.%m.%Y %H:%M:%S",
                    )
                except ValueError:
                    parse_errors += 1
                    continue

                if start_time is None:
                    start_time = timestamp
                if previous_time is not None:
                    interval = int((timestamp - previous_time).total_seconds())
                    if interval < 0:
                        backward = abs(interval)
                        if timestamp.date() == previous_time.date() and 1800 <= backward <= 3600:
                            ambiguous_clock_rollbacks.append(
                                {"file": path.name, "line": row_number, "backward_seconds": backward}
                            )
                        else:
                            parse_errors += 1
                    elif 0 < interval <= 120:
                        file_intervals[interval] += 1
                        sampling_intervals[interval] += 1
                previous_time = timestamp
                end_time = timestamp

                project = (row.get("PROJEKT_NAME") or "").strip()
                profile = (row.get("GASPROFIL_ID") or "").strip()
                if project:
                    file_projects.add(project)
                    project_names.add(project)
                if profile:
                    file_profiles.add(profile)
                    gas_profiles.add(profile)
                for slot in range(1, 4):
                    gas_id = (row.get(f"K{slot}_GAS_ID") or "").strip()
                    if gas_id:
                        file_components.add(gas_id)
                        component_ids.add(gas_id)
                file_mbw373_online |= _number_or_none(row.get("MBW373_ONLINE")) == 1

                calibration_raw = (row.get("KALIBRIERUNGEN_JSON") or "").strip()
                if calibration_raw:
                    calibration_payloads.append(calibration_raw)
                    try:
                        payload = json.loads(calibration_raw)
                        if not isinstance(payload, list):
                            raise ValueError("Kalibrierungspayload ist keine Liste")
                        calibration_entries += len(payload)
                    except (ValueError, TypeError):
                        parse_errors += 1

        summaries.append(
            {
                "path": path,
                "rows": file_rows,
                "start": start_time,
                "end": end_time,
                "intervals": file_intervals,
                "projects": file_projects,
                "profiles": file_profiles,
                "components": file_components,
                "mbw373_online": file_mbw373_online,
            }
        )

    if len(schemas) != 1:
        raise ValueError(f"Unterschiedliche CSV-Schemata gefunden: {len(schemas)}")
    if column_count != 252 or blank_columns != [2]:
        raise ValueError(f"Unerwartete CSV-Kopfzeile: {column_count} Spalten, leere Positionen {blank_columns}")
    if parse_errors or numeric_errors or row_shape_errors:
        raise ValueError(
            f"CSV-Validierung fehlgeschlagen: {parse_errors} Zeit/JSON, "
            f"{numeric_errors} Zahlen (ungültig oder nicht endlich), {row_shape_errors} Zeilenform"
        )
    if any(not item["rows"] for item in summaries):
        raise ValueError("Mindestens eine CSV enthält keine Datenzeilen.")

    example = next((item for item in summaries if item["components"] and item["mbw373_online"]), summaries[0])
    example_path = example["path"]
    point_indexes = {0, example["rows"] // 2, example["rows"] - 1}
    point_fields = (
        "AUTOMATIK_AKTIV", "AUTOMATIK_STATUS", "GASPROFIL_ID",
        "K1_GAS_ID", "K1_GAS_NAME_DE", "K1_KONZENTRATION", "K1_EINHEIT",
        "MBW373_ONLINE", "MBW373_ID", "MBW373_FROST_POINT_C",
        "MBW373_HEAD_PRESSURE_PA", "MBW373_EXTERNAL_TEMP_C", "MBW373_FLOW_L_MIN",
        "MBW373_STABLE", "KLIKA_C", "PT_PROZESS_C", "KELLER_T1_C",
        "KELLER_P1_bar", "A5B_CH01_mV",
    )
    point_samples = []
    with example_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        index = -1
        for row in reader:
            if tuple(row.get(key) for key in reader.fieldnames) == tuple(reader.fieldnames):
                continue
            index += 1
            if index not in point_indexes:
                continue
            point_samples.append(
                {
                    "source_row_number": reader.line_num,
                    "timestamp_local_no_timezone": f"{row.get('Datum', '')} {row.get('Uhrzeit', '')}",
                    "raw_source_fields": {field: row.get(field) or None for field in point_fields},
                }
            )

    example_start = example["start"].isoformat(timespec="seconds") if example["start"] else None
    example_end = example["end"].isoformat(timespec="seconds") if example["end"] else None
    reference_id = next(
        (point["raw_source_fields"]["MBW373_ID"] for point in point_samples
         if point["raw_source_fields"]["MBW373_ID"]),
        None,
    )
    preview = {
        "preview_only": True,
        "preview_schema_version": 3,
        "openbis_write_performed": False,
        "current_setup_reference": ({**setup_context, "applies_to_source_file": False,
            "association_status": "unassigned; confirm the setup used for this file"} if setup_context else None),
        "run_key": None,
        "source_file_key": {
            "value": f"LEGACY_FILE_SHA256:{hashlib.sha256(example_path.read_bytes()).hexdigest()}",
            "status": "file identity only; may cover parts of one or several sessions, not a run ID",
        },
        "source_file": {
            "path": example_path.name,
            "sha256": hashlib.sha256(example_path.read_bytes()).hexdigest(),
            "delimiter": "tab",
            "decimal_separator": ",",
            "columns": column_count,
            "rows": example["rows"],
            "first_record_local_no_timezone": example_start,
            "last_record_local_no_timezone": example_end,
            "timezone": None,
            "order": "original file order; never sort ambiguous local timestamps",
            "sampling_intervals_seconds": dict(example["intervals"]),
        },
        "openbis_path_proposal": {
            "space": "<existing FB 8.1 Lab Notebook Space; verify code>",
            "project": "GASI",
            "collection": "RUNS (Vorschlag; ausdrückliches Ziel konfigurieren)",
            "object_type": "EXPERIMENTAL_STEP",
            "object_code": "server generated; no openBIS object created",
        },
        "object_properties": {
            "source_project_labels": sorted(example["projects"]),
            "run_start": None,
            "run_end": None,
            "gas_profile_from_GASPROFIL_ID": sorted(example["profiles"]),
            "measurement_purpose": None,
            "dut_identifier": None,
            "dut_role": "physical gas sensor or gas-humidity sensor; existing identity, not a new device per stage",
        },
        "relationships": [
            {
                "direction": "INSTRUMENT parent -> EXPERIMENTAL_STEP",
                "source_device_text": reference_id,
                "inventory_identifier": None,
                "status": "device text is not an Inventory ID; resolve identity and reference role for this setup",
            }
        ],
        "datasets": [{"type": "RAW_DATA", "file": example_path.name}],
        "research_workflow": {
            "preparation": {"object_type":"EXPERIMENTAL_STEP","outputs":["test plan","nominal exposure profile"]},
            "measurement": {"object_type":"EXPERIMENTAL_STEP","activity":"gas/temperature/humidity exposure with simultaneous acquisition",
                            "dut_identifier":None,"dut_type":None,"raw_file_binding_confirmed":False},
            "analysis": {"object_type":"EXPERIMENTAL_STEP","parent":"measurement","outputs":["evaluated data","code","report"]},
            "exposure_conditions": {
                "gas":"nominal recipe; composition, unit and dry/wet basis required",
                "temperature":"setpoint and location required; KLIKA_C is chamber actual, not confirmed DUT temperature",
                "humidity":"quantity, unit, water/ice basis and temperature reference required; never infer dry gas from missing values",
                "duration":"explicit stage and repeat IDs; not one openBIS object per point or plateau"},
            "upload_ready":False,"next_configuration":"config/gasi_run.json; Notebook 08",
        },
        "unresolved": [
            "file-to-session mapping (SQLite archive or acquisition log); no automatic run grouping",
            "UTC offset/timezone and ambiguous repeated hour; CSV boundaries are not run start/end",
            "stage/repeat IDs and immutable recipe snapshot; status text is not a stage key",
            "DUT-to-A5B-channel mapping",
            "existing sensor identity, gas/temperature/humidity exposure profile and water/ice reference",
            "explicit data-record ranges for this run; a file is not automatically a complete run",
            "recipe/configuration snapshot used for this measurement",
            "calibration report and analyzed result file",
        ],
        "field_semantics": {
            "K1_KONZENTRATION": {"role": "gas-profile nominal composition", "unit_source": "K1_EINHEIT",
                                  "measured_reference": False, "delivered_concentration_confirmed": False},
            "MBW373_FROST_POINT_C": {"role": "candidate humidity reference", "unit": "degC",
                                      "requires": ["MBW373_ONLINE", "MBW373_STABLE", "device identity and measurement position"]},
            "A5B_CH01_mV": {"role": "unassigned raw voltage channel", "unit": "mV", "dut_identifier": None},
            "A5B_CH11_mV": {"role": "MGK temperature input according to current operating code", "unit": "mV",
                            "physical_assignment_confirmed_for_source_file": False},
            "KLIKA_C": {"role": "chamber actual temperature", "unit": "degC", "dut_temperature_confirmed": False},
            "PT_PROZESS_C": {"role": "process sensor", "unit": "degC", "physical_position": None},
            "MBW373_EXTERNAL_TEMP_C": {"role": "external hygrometer temperature channel", "unit": "degC", "physical_position": None},
            "MFC1_SOLL": {"role": "configured real-operation flow", "unit_source": "MFC1_UNIT",
                          "reference_conditions": "configuration used for this measurement and device validation required"},
            "KELLER_P1_bar": {"role": "pressure channel", "unit": "bar", "absolute_or_gauge": None, "physical_position": None},
            "quality": "keep raw text and status; blank is missing; zero may be default; MGK -100 may be sentinel",
        },
        "point_samples_saved_locally_only": point_samples,
    }
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "files_checked": len(summaries),
        "rows_checked": sum(item["rows"] for item in summaries),
        "schema_variants": len(schemas),
        "column_count": column_count,
        "parse_errors": parse_errors,
        "numeric_errors": numeric_errors,
        "row_shape_errors": row_shape_errors,
        "ambiguous_clock_rollbacks": ambiguous_clock_rollbacks,
        "sampling_intervals_seconds": dict(sampling_intervals.most_common(5)),
        "project_names": sorted(project_names),
        "gas_profiles": sorted(gas_profiles),
        "component_ids": sorted(component_ids),
        "calibration_entries": calibration_entries,
        "calibration_payloads_empty": all(value == "[]" for value in calibration_payloads),
        "preview_path": preview_path,
        "example_file": example_path,
        "example_points": len(point_samples),
        "message": "",
    }
