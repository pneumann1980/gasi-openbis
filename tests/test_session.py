"""Nur synthetische Credentials; zentrale Datei, Vorrang und Ausgabeschutz prüfen."""
from contextlib import redirect_stdout, redirect_stderr
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gasi_session as s


class SessionTests(unittest.TestCase):
    def test_one_switch_is_persistent_and_reread_across_kernel_contexts(self):
        self.assertFalse(s.writes_enabled())
        s.save_playground_token("SYNTHETIC_TOKEN_ONLY")
        self.assertIn("True", s.start_session(True))
        self.assertTrue(s.writes_enabled())
        import importlib.util
        spec = importlib.util.spec_from_file_location("fresh_gasi_session", s.__file__)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        fresh.SESSION_FILE = self.path
        self.assertTrue(fresh.writes_enabled())
        fresh.start_session(False)
        self.assertFalse(s.writes_enabled())
        self.assertEqual(s.session_value(s.TOKEN_ENV), "SYNTHETIC_TOKEN_ONLY")

    def test_environment_or_invalid_file_cannot_enable_writes(self):
        with patch.dict(os.environ, {s.WRITE_KEY: "true"}):
            self.assertFalse(s.writes_enabled())
            for value in ("yes", "1", "True please", ""):
                self.path.write_text(s.WRITE_KEY + "=" + value + "\n", encoding="utf-8")
                self.assertFalse(s.writes_enabled())
            self.path.write_text(s.WRITE_KEY + "=true\ninvalid private text\n", encoding="utf-8")
            self.assertFalse(s.writes_enabled())
        with self.assertRaises(s.SessionConfigError):
            s.start_session("True")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / ".env"
        self.environment = patch.dict(os.environ, dict.fromkeys(
            (s.TOKEN_ENV, "OTHER_SESSION", "SINGLE", "DOUBLE", "LITERAL"), ""))
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.location = patch.object(s, "SESSION_FILE", self.path)
        self.location.start()
        self.addCleanup(self.location.stop)

    def test_missing_credentials_provide_notebook_hint_without_creating_a_file(self):
        self.assertEqual(s.session_value(s.TOKEN_ENV), "")
        self.assertIn("GaSi_01_Session_starten.ipynb", s.session_status())
        self.assertFalse(self.path.exists())

    def test_save_and_reload_preserves_other_session_values(self):
        self.path.write_text('# Keep this comment\nOTHER_SESSION="private#value=$literal"\nOPENBIS_PLAYGROUND_TOKEN="OLD_FAKE"\n', encoding="utf-8")
        message = s.save_playground_token("NEW_FAKE_CENTRAL_TOKEN")
        self.assertNotIn("NEW_FAKE_CENTRAL_TOKEN", message)
        self.assertEqual(s.session_value(s.TOKEN_ENV), "NEW_FAKE_CENTRAL_TOKEN")
        self.assertEqual(s.session_value("OTHER_SESSION"), "private#value=$literal")
        self.assertIn("# Keep this comment", self.path.read_text(encoding="utf-8"))
        self.assertEqual(self.path.read_text(encoding="utf-8").count(s.TOKEN_ENV + "="), 1)
        self.assertEqual(os.environ[s.TOKEN_ENV], "")  # Nicht alle Secrets in die Prozessumgebung kopieren.
        self.assertFalse(list(self.path.parent.glob(".env.*.tmp")))

    def test_environment_has_precedence_and_file_is_not_cached(self):
        s.save_playground_token("FIRST_FAKE")
        with patch.dict(os.environ, {s.TOKEN_ENV: "ENV_FAKE"}):
            self.assertEqual(s.session_value(s.TOKEN_ENV), "ENV_FAKE")
            self.assertIn("Umgebungsvariable", s.session_status())
        s.save_playground_token("SECOND_FAKE")
        self.assertEqual(s.session_value(s.TOKEN_ENV), "SECOND_FAKE")

    def test_empty_entry_never_clears_credentials_or_creates_a_file(self):
        s.save_playground_token("")
        self.assertFalse(self.path.exists())
        s.save_playground_token("KEEP_FAKE")
        original = self.path.read_bytes()
        s.save_playground_token("   ")
        self.assertEqual(self.path.read_bytes(), original)

    def test_quotes_comments_and_literals_without_execution_or_expansion(self):
        self.path.write_text('OPENBIS_PLAYGROUND_TOKEN= # not configured\nSINGLE=\'a # b\' # note\nDOUBLE="c#d" # note\nLITERAL=$(do-not-run)\n', encoding="utf-8")
        self.assertEqual(s.session_value(s.TOKEN_ENV), "")
        self.assertEqual(s.session_value("SINGLE"), "a # b")
        self.assertEqual(s.session_value("DOUBLE"), "c#d")
        self.assertEqual(s.session_value("LITERAL"), "$(do-not-run)")

    def test_invalid_file_never_discloses_values_or_gets_overwritten(self):
        for content in ('OPENBIS_PLAYGROUND_TOKEN="FAKE_SECRET\n',
                        'OPENBIS_PLAYGROUND_TOKEN=FAKE_SECRET\nOPENBIS_PLAYGROUND_TOKEN=OTHER\n',
                        'FAKE_SECRET_NOT_AN_ASSIGNMENT\n'):
            self.path.write_text(content, encoding="utf-8")
            status = s.session_status()
            self.assertNotIn("FAKE_SECRET", status)
            with self.assertRaises(s.SessionConfigError) as raised:
                s.save_playground_token("ANOTHER_FAKE")
            self.assertNotIn("FAKE_SECRET", str(raised.exception))
            self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_token_roundtrip_handles_quotes_and_rejects_embedded_newlines(self):
        secret = 'FAKE"token#=$\\value'
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            message = s.save_playground_token(secret)
            status = s.session_status()
        self.assertEqual(s.session_value(s.TOKEN_ENV), secret)
        self.assertNotIn(secret, output.getvalue() + message + status)
        with self.assertRaises(s.SessionConfigError):
            s.save_playground_token("FAKE\nSECOND_LINE")
        self.assertEqual(s.session_value(s.TOKEN_ENV), secret)

    def test_failed_atomic_write_preserves_previous_file_without_leaking(self):
        s.save_playground_token("KEEP_FAKE")
        original = self.path.read_bytes()
        with patch.object(s.os, "replace", side_effect=OSError("NEW_FAKE_SECRET")):
            with self.assertRaises(s.SessionConfigError) as raised:
                s.save_playground_token("NEW_FAKE_SECRET")
        self.assertNotIn("NEW_FAKE_SECRET", str(raised.exception))
        self.assertEqual(original, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
