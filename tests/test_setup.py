"""Current setup: no false confirmation, duplicate identity or automatic CSV linkage."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from gasi_setup import inspect_setup, measurement_context, show_setup_summary, write_setup_report


def setup_fixture():
    return {"schema_version": 1, "scope": "current_only", "setup_id": "SYNTHETIC_SETUP",
            "verified_on": "2026-11-12", "modules": {"mixing": "Synthetic module"}, "channels": [],
            "devices": [{"position": "MFC1", "module": "mixing", "kind": "mfc", "quantity": "normal_volume_flow",
                         "manufacturer": "Synthetic", "model": "Synthetic", "serial_number": "PRIVATE-SYNTHETIC-ID",
                         "installed_confirmed": True, "evidence": ["synthetic fixture"], "calibration_status": "assessed",
                         "range_max": 10, "unit": "mln/min", "reference_temperature_C": 0,
                         "reference_pressure_hPa_abs": 1013.25, "design_gas": "AIR", "calibration_medium": "AIR", "operation_gas": "AIR"}]}


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "setup.json"

    def inspect(self, config):
        self.path.write_text(json.dumps(config), encoding="utf-8")
        return inspect_setup(self.path)

    def test_missing_file_has_actionable_hint_and_no_side_effects(self):
        result = inspect_setup(self.path)
        self.assertFalse(result["available"])
        self.assertIn("example.json", result["message"])
        self.assertFalse(self.path.exists())

    def test_documented_device_does_not_confirm_installation_or_status(self):
        cfg = setup_fixture()
        self.assertTrue(self.inspect(cfg)["ready"])
        cfg["devices"][0]["installed_confirmed"] = False
        self.assertFalse(self.inspect(cfg)["ready"])
        cfg["devices"][0]["installed_confirmed"] = True
        cfg["devices"][0]["open_issues"] = ["Conflicting range"]
        self.assertFalse(self.inspect(cfg)["ready"])

    def test_duplicate_positions_or_serials_are_rejected(self):
        for same_position in (True, False):
            cfg = setup_fixture()
            second = deepcopy(cfg["devices"][0])
            if not same_position:
                second["position"] = "MFC2"
                second["serial_number"] = " private-synthetic-id "
            cfg["devices"].append(second)
            with self.assertRaises(ValueError):
                self.inspect(cfg)

    def test_unknown_or_nonfinite_flow_and_reference_conditions_stay_open(self):
        for field, value in (("range_max", float("nan")), ("range_max", float("inf")),
                             ("reference_temperature_C", -274), ("reference_pressure_hPa_abs", 0),
                             ("calibration_medium", None), ("operation_gas", None)):
            cfg = setup_fixture()
            cfg["devices"][0][field] = value
            self.assertFalse(self.inspect(cfg)["ready"], field)

    def test_channel_requires_existing_device_location_and_confirmation(self):
        cfg = setup_fixture()
        cfg["channels"] = [{"name": "SYNTHETIC", "device_position": "OTHER", "confirmed": True}]
        with self.assertRaises(ValueError):
            self.inspect(cfg)
        cfg["channels"][0]["device_position"] = "MFC1"
        self.assertFalse(self.inspect(cfg)["ready"])

    def test_current_context_is_never_an_assignment_to_existing_measurements(self):
        context = measurement_context(self.inspect(setup_fixture()))
        self.assertTrue(context["setup_checked_locally"])
        self.assertFalse(context["applies_to_source_file"])
        self.assertIn("configuration_sha256", context)

    def test_private_details_stay_in_local_report_and_are_html_escaped(self):
        cfg = setup_fixture()
        cfg["devices"][0]["open_issues"] = ["<script>PRIVATE-DETAIL</script>"]
        report = self.inspect(cfg)
        output = io.StringIO()
        with redirect_stdout(output):
            show_setup_summary(report)
        self.assertNotIn("PRIVATE-SYNTHETIC-ID", output.getvalue())
        self.assertNotIn("PRIVATE-DETAIL", output.getvalue())
        target = self.path.with_suffix(".html")
        original = self.path.read_bytes()
        write_setup_report(report, target)
        document = target.read_text(encoding="utf-8")
        self.assertIn("PRIVATE-SYNTHETIC-ID", document)
        self.assertNotIn("<script>", document)
        self.assertIn("&lt;script&gt;", document)
        self.assertEqual(original, self.path.read_bytes())

    def test_public_template_stays_a_draft_and_history_is_out_of_scope(self):
        template = Path(__file__).resolve().parents[1] / "config/gasi_setup.example.json"
        self.assertFalse(inspect_setup(template)["ready"])
        cfg = setup_fixture()
        cfg["scope"] = "history"
        with self.assertRaises(ValueError):
            self.inspect(cfg)


if __name__ == "__main__":
    unittest.main()
