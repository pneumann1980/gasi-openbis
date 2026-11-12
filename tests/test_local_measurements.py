"""Small synthetic exports exercising the legacy 252-column schema, no real data."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gasi_local_measurements import NUMERIC_FIELDS, inspect_measurements


def fixture(directory, changes=None, truncate=False, extra=False, repeated_header=False):
    fields = ["Datum", "Uhrzeit", "", *NUMERIC_FIELDS, "PROJEKT_NAME", "GASPROFIL_ID", "MBW373_ID",
              "KALIBRIERUNGEN_JSON", "K1_GAS_ID", "K1_EINHEIT"]
    fields.extend(f"UNUSED_{i}" for i in range(252 - len(fields)))
    values = dict.fromkeys(fields, "")
    values.update(Datum="11.11.2026", Uhrzeit="12:00:00", KLIKA_C="25,5",
                  PROJEKT_NAME="SYNTHETIC", MBW373_ID="synthetic device text", KALIBRIERUNGEN_JSON="[]")
    values.update(changes or {})
    row = [values[key] for key in fields]
    path = Path(directory) / "synthetic.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(fields)
        if repeated_header:
            writer.writerow(fields)
        writer.writerow(row[:-1] if truncate else row + ["EXTRA"] if extra else row)
    return path


class LocalMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.preview = self.folder / "preview.json"

    def inspect(self):
        return inspect_measurements(self.folder, self.preview)

    def test_empty_or_missing_directory(self):
        self.assertEqual(self.inspect()["files_checked"], 0)
        self.assertEqual(inspect_measurements(self.folder / "missing", self.preview)["files_checked"], 0)
        self.assertFalse(self.preview.exists())

    def test_current_setup_is_not_automatically_assigned_even_if_caller_requests_it(self):
        fixture(self.folder)
        inspect_measurements(self.folder, self.preview, setup_context={
            "setup_id": "SYNTHETIC_CURRENT", "applies_to_source_file": True})
        context = json.loads(self.preview.read_text(encoding="utf-8"))["current_setup_reference"]
        self.assertFalse(context["applies_to_source_file"])
        self.assertEqual(context["setup_id"], "SYNTHETIC_CURRENT")

    def test_short_and_long_rows_rejected_without_changing_source(self):
        for mode in ("truncate", "extra"):
            with self.subTest(mode=mode):
                path = fixture(self.folder, **{mode: True})
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "1 Zeilenform"):
                    self.inspect()
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(self.preview.exists())

    def test_invalid_nonfinite_numbers_rejected_in_every_evaluated_channel(self):
        for field in NUMERIC_FIELDS:
            for value in ("invalid", "NaN", "inf", "-Infinity", "1e309"):
                with self.subTest(field=field, value=value):
                    path = fixture(self.folder, {field: value})
                    before = path.read_bytes()
                    with self.assertRaisesRegex(ValueError, "1 Zahlen"):
                        self.inspect()
                    self.assertEqual(path.read_bytes(), before)
                    self.assertFalse(self.preview.exists())

    def test_decimal_comma_blank_and_real_zero_preserved(self):
        path = fixture(self.folder, {"A5B_CH01_mV": "0,000000", "MBW373_FROST_POINT_C": ""})
        before = path.read_bytes()
        self.assertEqual(self.inspect()["rows_checked"], 1)
        preview = json.loads(self.preview.read_text(encoding="utf-8"))
        point = preview["point_samples_saved_locally_only"][0]["raw_source_fields"]
        self.assertEqual(point["A5B_CH01_mV"], "0,000000")
        self.assertIsNone(point["MBW373_FROST_POINT_C"])
        self.assertIsNone(preview["object_properties"]["run_start"])
        self.assertIsNone(preview["relationships"][0]["inventory_identifier"])
        self.assertEqual(path.read_bytes(), before)
        self.assertIsNone(preview["run_key"])
        self.assertIn(hashlib.sha256(before).hexdigest(), preview["source_file_key"]["value"])

    def test_repeated_header_does_not_shift_preview_source_line(self):
        fixture(self.folder, repeated_header=True)
        self.assertEqual(self.inspect()["rows_checked"], 1)
        preview = json.loads(self.preview.read_text(encoding="utf-8"))
        self.assertEqual(preview["point_samples_saved_locally_only"][0]["source_row_number"], 3)

    def test_original_cannot_be_used_as_preview_destination(self):
        path = fixture(self.folder)
        with self.assertRaisesRegex(ValueError, "Original-CSV"):
            inspect_measurements(self.folder, path)

    def test_calibration_payload_must_be_a_list(self):
        fixture(self.folder, {"KALIBRIERUNGEN_JSON": "{}"})
        with self.assertRaisesRegex(ValueError, "1 Zeit/JSON"):
            self.inspect()
        self.assertFalse(self.preview.exists())


if __name__ == "__main__":
    unittest.main()
