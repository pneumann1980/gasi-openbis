"""Die Projektumgebung darf keine passende venv ablehnen oder in fremdes Python installieren."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def cell(path, tag):
    return next(c.source for c in nbformat.read(path, as_version=4).cells if tag in c.metadata.get("tags", []))


class ProjectSetupTests(unittest.TestCase):
    def test_venv_without_conda_or_expected_name_is_accepted_in_both_notebooks(self):
        for path in (ROOT / "GaSi_02_Einmalig_einrichten.ipynb", ROOT / "example/pybis_workshop_exercises.ipynb"):
            for python_version in ((3, 10, 0), (3, 14, 4)):
                with patch.object(sys, "version_info", python_version), \
                     patch.object(sys, "prefix", str(ROOT / "ordinary_python")), redirect_stdout(io.StringIO()):
                    exec(cell(path, "check-environment"), {})
            with patch.object(sys, "version_info", (3, 9, 0)), redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):
                    exec(cell(path, "check-environment"), {})

    def test_installation_uses_kernel_executable_and_handles_paths_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="gasi project ") as temp:
            root = Path(temp)
            for name in ("requirements-dev.txt", "requirements-playground.txt", "requirements-docs.txt"):
                (root / name).write_text("# synthetic requirements\n", encoding="utf-8")
            nested = root / "example folder"
            nested.mkdir()
            with patch.object(Path, "cwd", return_value=nested), \
                 patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run, \
                 redirect_stdout(io.StringIO()):
                exec(cell(ROOT / "GaSi_02_Einmalig_einrichten.ipynb", "install-requirements"), {})
            run.assert_called_once_with(
                [sys.executable, "-m", "pip", "install", "-r", str(root / "requirements-dev.txt")], check=True)

    def test_missing_repository_does_not_attempt_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(Path, "cwd", return_value=Path(temp)), patch.object(subprocess, "run") as run:
                with self.assertRaises(RuntimeError):
                    exec(cell(ROOT / "GaSi_02_Einmalig_einrichten.ipynb", "install-requirements"), {})
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
