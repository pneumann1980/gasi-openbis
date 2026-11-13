"""Device identity, asset candidates and real-device import safety; synthetic fixtures only."""
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from test_playground import things
from test_playground_provision import ProvisionClient
import gasi_inventory as local
import gasi_inventory_openbis as remote
import gasi_openbis_playground as g
import gasi_session as session


def write_identity_pdf(path, content):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=200)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
        DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 100 Td ({content}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)


def fixture(root):
    private = root / "data/datasheets"
    private.mkdir(parents=True)
    (root / "config").mkdir()
    write_identity_pdf(private / "device.pdf", "ExampleMaker TEST-MODEL-ONE SN-00123")
    device = dict(position="MFC1", manufacturer="ExampleMaker", model="TEST-MODEL-ONE",
                  serial_number="SN-00123", kind="mfc", range_max=100,
                  installed_confirmed=False, calibration_status="not_assessed",
                  evidence=[dict(file="data/datasheets/device.pdf", page=1)])
    setup = dict(scope="current_only", setup_id="TEST_CURRENT", devices=[device])
    (root / "config/gasi_setup.json").write_text(json.dumps(setup), encoding="utf-8")
    (private / "test_Inventar.csv").write_bytes((
        'Inventarnummer;OE;Preis;Leistungsbeschreibung\n'
        '000123/0001;=" 8.1";9876,54;Massendurchflussregler bis 100 mL/min\n'
        '000123/0002;=" 8.1";9876,54;Massendurchflussregler bis 100 mL/min\n').encode("cp1252"))
    return setup


class InventoryClient(ProvisionClient):
    def __init__(self):
        super().__init__()
        assignments = self.types["INSTRUMENT"].data["propertyAssignments"]
        for code, dtype in (("DEVICE_MODEL_NAME", "VARCHAR"), ("NOTES", "MULTILINE_VARCHAR"),
                            ("INVENTORY_NO", "INTEGER"), ("INVENTORY_NO_ADD", "INTEGER")):
            assignments.append(dict(propertyType=dict(code=code, dataType=dtype), mandatory=False,
                plugin=None, registrationDate=None, showInEditView=True))

    def get_samples(self, type=None, space=None, code=None, attrs=None, props=None):
        return things([self.get_sample(key) for key, data in self.samples.items()
                       if (space is None or data["space"] == space)
                       and (code is None or data["code"] == code)
                       and (type is None or data["type"] == type)])

    def get_vocabulary(self, code):
        if code in ("BAM_OE", "BAM_LOCATION_COMPLETE"):
            return SimpleNamespace(get_terms=lambda: self.get_terms(vocabulary=code))
        return super().get_vocabulary(code)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        switch = patch.object(session, "SESSION_FILE", self.root / ".env")
        switch.start()
        self.addCleanup(switch.stop)
        self.setup = fixture(self.root)
        self.client = InventoryClient()
        self.settings = remote.default_settings()
        self.settings["location"] = dict(code="TEST_EXISTING_LOCATION", confirmed=True, evidence="Synthetic room fixture")

    def write_setup(self):
        (self.root / "config/gasi_setup.json").write_text(json.dumps(self.setup), encoding="utf-8")

    def report(self):
        return local.build_assignment_report(self.root)

    def state(self):
        return remote.read_instance(self.client, self.settings)

    def register(self):
        return remote.ensure_devices(self.client, self.report(), self.settings, self.state(), self.root)

    def test_pdf_identity_is_separate_from_current_installation_and_calibration(self):
        row = self.report()["rows"][0]
        self.assertTrue(row["identity_verified"])
        self.assertFalse(row["installed_confirmed"])
        self.assertEqual(row["calibration_status"], "not_assessed")

    def test_ambiguous_assets_preserve_zeros_and_do_not_assign_by_equal_range(self):
        report = self.report()
        row = report["rows"][0]
        self.assertEqual([c["number"] for c in row["asset_candidates"]], ["000123/0001", "000123/0002"])
        self.assertIsNone(row["inventory_number"])
        self.assertNotIn("9876", json.dumps(report))
        self.assertEqual(report["register_rows"], 2)

    def test_short_asset_row_is_rejected(self):
        path = self.root / "data/datasheets/test_Inventar.csv"
        path.write_text("Inventarnummer;OE;Preis;Leistungsbeschreibung\n1/001;8.1;0\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            local.read_register(path)

    def test_wrong_pdf_page_or_serial_blocks_identity(self):
        for field, value in (("page", 2), ("serial", "SN-OTHER")):
            with self.subTest(field=field):
                candidate = deepcopy(self.setup["devices"][0])
                if field == "page":
                    candidate["evidence"][0]["page"] = value
                else:
                    candidate["serial_number"] = value
                verified, _, _ = local.verify_identity(candidate, self.root)
                self.assertFalse(verified)

    def test_image_review_is_bound_to_hash_and_exact_identity(self):
        path = self.root / "data/datasheets/label.jpg"
        path.write_bytes(b"SYNTHETIC LABEL REVIEW FIXTURE")
        candidate = deepcopy(self.setup["devices"][0])
        review = {key: candidate[key] for key in ("manufacturer", "model", "serial_number")}
        review.update(method="visual_label_review", sha256=sha256(path.read_bytes()).hexdigest(), reviewed_at="2026-01-01T00:00:00Z")
        candidate["evidence"] = [dict(file="data/datasheets/label.jpg", identity_review=review)]
        self.assertTrue(local.verify_identity(candidate, self.root)[0])
        path.write_bytes(b"CHANGED FIXTURE")
        self.assertFalse(local.verify_identity(candidate, self.root)[0])

    def test_duplicate_identity_is_not_registered_twice(self):
        second = deepcopy(self.setup["devices"][0])
        second["position"] = "MFC2"
        self.setup["devices"].append(second)
        self.write_setup()
        self.assertTrue(all(not row["identity_verified"] for row in self.report()["rows"]))
        self.register()
        self.assertFalse(self.client.created)

    def test_device_code_does_not_depend_on_position_or_model(self):
        device = self.setup["devices"][0]
        changed = {**device, "position": "NEW_POSITION", "model": "Corrected model"}
        self.assertEqual(local.device_code(device), local.device_code(changed))
        changed["serial_number"] = "SN-00124"
        self.assertNotEqual(local.device_code(device), local.device_code(changed))

    def test_no_real_location_never_uses_synthetic_test_placeholder(self):
        self.settings["location"] = dict(code="", confirmed=False, evidence="")
        before = (self.root / "config/gasi_setup.json").read_bytes()
        result = self.register()
        self.assertEqual(result["rows"][0]["registration_status"], "location_open")
        self.assertFalse(self.client.created)
        self.assertFalse(self.client.saved)
        self.assertEqual((self.root / "config/gasi_setup.json").read_bytes(), before)
        self.assertNotIn("registered_at", result)
        with patch("gasi_session.writes_enabled", return_value=True), patch.object(remote, "load_inventory_settings", return_value=(self.settings, "FAKE")),  \
                patch.object(g, "connect_playground", return_value=(self.client, "FAKE")):
            _, message = remote.register_inventory(root=self.root)
        self.assertIn("Keine Geräte angelegt", message)
        self.assertIn("Standort", message)

    def test_full_registration_repeat_and_id_backfill_preserve_setup_statuses(self):
        first = self.register()
        second = self.register()
        self.assertEqual(first["rows"][0]["registration_status"], "created")
        self.assertEqual(second["rows"][0]["registration_status"], "reuse")
        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(len(self.client.saved), 2)
        setup = json.loads((self.root / "config/gasi_setup.json").read_text())
        self.assertFalse(setup["devices"][0]["installed_confirmed"])
        self.assertEqual(setup["devices"][0]["calibration_status"], "not_assessed")
        self.assertEqual(setup["devices"][0]["openbis_identifier"], first["rows"][0]["openbis"]["identifier"])
        self.assertEqual(first["rows"][0]["inventory_number"], None)

    def test_resume_after_committed_device_save_does_not_duplicate(self):
        self.client.fail_after = local.device_code(self.setup["devices"][0])
        with self.assertRaises(TimeoutError):
            self.register()
        result = self.register()
        self.assertEqual(result["rows"][0]["registration_status"], "reuse")
        self.assertEqual(len(self.client.samples), 1)
        self.assertEqual(len(self.client.created), 1)

    def test_confirmed_asset_splits_integer_fields_and_preserves_raw_reference(self):
        self.setup["devices"][0]["inventory_assignment"] = dict(confirmed=True, number="000123/0002", evidence=["synthetic sticker proof"])
        self.write_setup()
        row = self.register()["rows"][0]
        self.assertEqual(row["properties"]["INVENTORY_NO"], 123)
        self.assertEqual(row["properties"]["INVENTORY_NO_ADD"], 2)
        self.assertIn("000123/0002", row["properties"]["NOTES"])

    def test_precise_user_location_is_preserved_beyond_broader_controlled_room(self):
        self.settings["location"].update(
            reported_text="SYNTHETIC SITE, house TEST, room 01 A", label="SYNTHETIC/TEST/01",
            precision="broader_controlled_room", mapping_note="Room suffix A is kept as additional detail.")
        row = self.register()["rows"][0]
        notes = json.loads(row["properties"]["NOTES"])
        self.assertEqual(notes["location"]["reported_text"], "SYNTHETIC SITE, house TEST, room 01 A")
        self.assertEqual(notes["location"]["precision"], "broader_controlled_room")
        path = local.write_assignment_report(self.register(), self.root / "report")
        html = path.read_text(encoding="utf-8")
        self.assertIn("room 01 A", html)
        self.assertIn("Room suffix A", html)

    def test_existing_model_conflict_never_creates_a_second_device(self):
        first = self.register()["rows"][0]
        key = first["openbis"]["identifier"]
        self.client.samples[key]["props"]["device_model_name"] = "OTHER-MODEL"
        result = self.register()
        self.assertEqual(result["rows"][0]["registration_status"], "conflict")
        self.assertEqual(len(self.client.created), 1)

    def test_unreadable_saved_device_reference_blocks_duplicate_creation(self):
        self.setup["devices"][0]["openbis_identifier"] = "/OTHER/UNREADABLE"
        self.write_setup()
        result = self.register()
        self.assertEqual(result["rows"][0]["registration_status"], "conflict")
        self.assertFalse(self.client.created)

    def test_default_entrypoint_never_connects(self):
        with patch.object(g, "connect_playground", side_effect=AssertionError("No network in preview")):
            result, message = remote.register_inventory()
        self.assertIsNone(result)
        self.assertIn("deaktiviert", message)

    def test_real_target_settings_preserve_synthetic_section_and_need_no_synthetic_paths(self):
        path = self.root / "config/targets.json"
        synthetic = dict(instrument=dict(name="SYNTHETIC UNCHANGED"), lab_notebook=dict(space=""),
                         inventory=dict(space=""))
        path.write_text(json.dumps(synthetic), encoding="utf-8")
        remote.save_inventory_settings(self.settings, path)
        result = json.loads(path.read_text())
        self.assertEqual(result["instrument"], synthetic["instrument"])
        self.assertEqual(result["gasi_inventory"], self.settings)

    def test_local_html_escapes_private_descriptions_and_sources_remain_unchanged(self):
        source = self.root / "data/datasheets/test_Inventar.csv"
        before = source.read_bytes()
        report = self.report()
        report["rows"][0]["open_issues"].append("<script>PRIVATE-ONLY</script>")
        report["rows"][0]["openbis"] = dict(identifier="FAKE-ID", url="javascript:alert(1)")
        path = local.write_assignment_report(report, self.root / "report")
        self.assertIn("&lt;script&gt;", path.read_text(encoding="utf-8"))
        self.assertNotIn("<script>", path.read_text(encoding="utf-8"))
        self.assertNotIn("javascript:", path.read_text(encoding="utf-8"))
        output = io.StringIO()
        with patch("sys.stdout", output):
            local.show_assignment_summary(report)
        self.assertNotIn("SN-00123", output.getvalue())
        self.assertEqual(before, source.read_bytes())
