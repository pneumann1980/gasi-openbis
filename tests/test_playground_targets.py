"""Local targets are explicit; no per-target write permission or approval strings."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import gasi_openbis_playground as ob
from gasi_playground_targets import collection_codes, initialize_target_config, save_target_config, show_target_editor

class TargetConfigTests(unittest.TestCase):
    def test_default_path_is_repository_bound_even_from_another_cwd(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'targets.json'
            initialize_target_config(path)
            cwd = Path.cwd()
            try:
                os.chdir(temp)
                with patch.object(ob, 'TARGET_CONFIG_PATH', path):
                    config, message = ob.load_target_config()
                self.assertIsInstance(config, dict)
                self.assertIn(path.as_posix(), message)
            finally:
                os.chdir(cwd)

    def test_initialize_preserves_existing_configuration_and_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'targets.json'
            cfg, _ = initialize_target_config(path)
            self.assertNotIn('approved_test_scope', cfg)
            cfg['inventory']['space'] = 'EXISTING'
            path.write_text(json.dumps(cfg), encoding='utf-8')
            original = path.read_bytes()
            self.assertEqual(initialize_target_config(path)[0], cfg)
            self.assertEqual(path.read_bytes(), original)
            path.write_text('{invalid', encoding='utf-8')
            self.assertIsNone(initialize_target_config(path)[0])
            self.assertEqual(path.read_text(), '{invalid')

    def test_save_requires_exact_paths_but_no_approval_flags_or_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'targets.json'
            cfg, _ = initialize_target_config(path)
            with self.assertRaises(ob.CheckFailed):
                save_target_config(cfg, path)
            for bad in ('SPACE/PROJECT/COLLECTION', '/A/B', '/A/B/C/D', '/A/B/<C>'):
                with self.assertRaises(ob.CheckFailed):
                    collection_codes(bad)
            cfg['lab_notebook'] = collection_codes('/8.1_TEST/GASI_TEST/RUNS')
            cfg['inventory'] = collection_codes('/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS')
            save_target_config(cfg, path)
            self.assertEqual(ob.load_target_config(path)[0], cfg)

    def test_editor_save_button_has_no_additional_write_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'targets.json'
            with patch('IPython.display.display'), redirect_stdout(io.StringIO()), patch.object(
                    ob, 'connect_playground', side_effect=AssertionError('Local editor must stay offline')):
                editor = show_target_editor(path)
                lab, inventory, advanced, button, _ = editor.children
                lab.value = '/8.1_TEST/GASI_TEST/RUNS'
                inventory.value = '/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS'
                button.click()
                cfg, _ = ob.load_target_config(path)
                self.assertEqual(cfg['test_scope']['inventory_path_prefix'], inventory.value)
                self.assertNotIn('approved_test_scope', cfg)
                editor.close()
