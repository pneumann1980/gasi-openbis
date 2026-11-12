"""Local target configuration is shared, explicit and independent of kernel cwd."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gasi_openbis_playground as playground
from gasi_playground_targets import collection_codes, initialize_target_config, save_target_config, show_target_editor


class TargetConfigTests(unittest.TestCase):
    def test_default_path_is_repository_bound_even_from_another_cwd(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config/targets.json"
            initialize_target_config(path)
            original = Path.cwd()
            try:
                os.chdir(temp)
                with patch.object(playground, "TARGET_CONFIG_PATH", path):
                    config, message = playground.load_target_config()
                self.assertIsInstance(config, dict)
                self.assertIn(path.as_posix(), message)
            finally:
                os.chdir(original)
        self.assertEqual(playground.TARGET_CONFIG_PATH.parent.parent, Path(playground.__file__).resolve().parent)

    def test_initialize_preserves_existing_configuration_and_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "targets.json"
            cfg, _ = initialize_target_config(path)
            self.assertFalse(cfg["approved_test_scope"]["steward_approved"])
            cfg["inventory"]["space"] = "EXISTING"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            original = path.read_bytes()
            self.assertEqual(initialize_target_config(path)[0], cfg)
            self.assertEqual(path.read_bytes(), original)
            path.write_text("{invalid", encoding="utf-8")
            self.assertIsNone(initialize_target_config(path)[0])
            self.assertEqual(path.read_text(), "{invalid")

    def test_save_requires_exact_paths_and_reference_for_confirmed_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "targets.json"
            cfg, _ = initialize_target_config(path)
            original = path.read_bytes()
            with self.assertRaises(playground.CheckFailed):
                save_target_config(cfg, path)
            self.assertEqual(path.read_bytes(), original)
            for bad in ("SPACE/PROJECT/COLLECTION", "/A/B", "/A/B/C/D", "/A/B/<C>"):
                with self.assertRaises(playground.CheckFailed):
                    collection_codes(bad)
            cfg["lab_notebook"] = collection_codes("/FB81_LAB/TEST/RUNS")
            cfg["inventory"] = collection_codes("/FB81_INVENTORY/TEST/INSTRUMENTS")
            save_target_config(cfg, path)
            self.assertFalse(playground.load_target_config(path)[0]["approved_test_scope"]["steward_approved"])
            cfg["approved_test_scope"]["steward_approved"] = True
            with self.assertRaises(playground.CheckFailed):
                save_target_config(cfg, path)

    def test_editor_save_button_persists_targets_without_connecting_or_enabling_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "targets.json"
            with patch("IPython.display.display"), redirect_stdout(io.StringIO()), patch.object(
                    playground, "connect_playground", side_effect=AssertionError("No connection in local editor")):
                editor = show_target_editor(path)
                lab, inventory, approved, reference, advanced, button, _ = editor.children
                self.assertFalse(approved.value)
                lab.value = "/FB81_LAB/TEST/RUNS"
                inventory.value = "/FB81_INVENTORY/TEST/INSTRUMENTS"
                button.click()
                cfg, _ = playground.load_target_config(path)
                self.assertEqual(playground.target_path(cfg["lab_notebook"]), lab.value)
                self.assertEqual(cfg["approved_test_scope"]["inventory_path_prefix"], inventory.value)
                self.assertFalse(cfg["approved_test_scope"]["steward_approved"])
                approved.value = True
                button.click()  # Missing reference must leave the previous file intact.
                self.assertFalse(playground.load_target_config(path)[0]["approved_test_scope"]["steward_approved"])
                reference.value = "LOCAL FAKE APPROVAL"
                button.click()
                self.assertTrue(playground.load_target_config(path)[0]["approved_test_scope"]["steward_approved"])
                editor.close()
