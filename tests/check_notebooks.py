"""Validate/execute notebooks in fresh kernels; never save executed outputs.

Run from repository root: python tests/check_notebooks.py
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
import nbformat

ROOT = Path(__file__).resolve().parents[1]
SESSION_NOTEBOOK = "GaSi_00_Session_einrichten.ipynb"
PROJECT_NOTEBOOK = "GaSi_Projekt_einrichten.ipynb"
TARGET_NOTEBOOK = "GaSi_Playground_Ziele_einrichten.ipynb"
PROVISION_NOTEBOOK = "GaSi_Playground_Testbereich_anlegen.ipynb"
NOTEBOOKS = ("GaSi_01_Datenmodell_HTML_erzeugen.ipynb", "GaSi_02_Aktuelles_Setup_pruefen.ipynb",
             "GaSi_03_Messdateien_pruefen.ipynb", "GaSi_04_Playground_Bestand_lesen.ipynb", "GaSi_05_Playground_Schreibtest.ipynb")


def execute(path, cwd, spec_dir, *, fake=False, write=False, repeat=False, enter_token=None, session_file=None, simulate_install=False, provision=False):
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    # Der Nutzer darf parallel Notebook-Statusausgaben speichern. Für den Test
    # ausschließlich eine im Speicher bereinigte Kopie mit frischem Kernel verwenden.
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    setup = '''import socket
network_attempts = []
def forbid_network(*args, **kwargs):
    network_attempts.append(True)
    raise AssertionError("External network forbidden in local notebook tests")
socket.create_connection = forbid_network
socket.socket.connect = forbid_network
'''
    credential_path = session_file or (spec_dir / (path.stem + "_session.env"))
    setup += f"""
from pathlib import Path
import gasi_session as session
session.SESSION_FILE = Path({str(credential_path)!r})
"""
    if path.name in NOTEBOOKS[3:]:
        setup += f"""
import gasi_openbis_playground as playground
playground.DISCOVERY_REPORT_PATH = Path({str(spec_dir / 'read_discovery.json')!r})
"""
    if simulate_install:
        setup += '''
import subprocess
import sys
install_calls = []
def simulate_pip_install(args, **kwargs):
    assert args[:5] == [sys.executable, "-m", "pip", "install", "-r"]
    assert len(args) == 6 and Path(args[5]).is_file()
    assert Path(args[5]).name == "requirements-dev.txt"
    assert kwargs == {"check": True}
    install_calls.append(args)
    return subprocess.CompletedProcess(args, 0)
'''
    for cell in nb.cells:
        if "install-requirements" in cell.metadata.get("tags", []):
            assert simulate_install, "Requirements-Installation in Notebook-Tests ausdrücklich simulieren"
            cell.source = cell.source.replace("subprocess.run(", "simulate_pip_install(")
    if simulate_install:
        nb.cells.append(nbformat.v4.new_code_cell("assert len(install_calls) == 1"))
    if fake:
        setup += f"""
import sys
sys.path.insert(0, {str(ROOT / 'tests')!r})
from test_playground import FakeClient
import gasi_openbis_playground as g
fake = FakeClient()
g.connect_playground = lambda: (fake, "LOCAL FAKE CLIENT; no network")
g.load_target_config = lambda: (fake.cfg, "LOCAL FAKE CONFIG; not real BAM paths")
"""
        if path.name == PROVISION_NOTEBOOK:
            setup += f"""
from test_playground_provision import ProvisionClient
fake = ProvisionClient()
g.connect_playground = lambda: (fake, "LOCAL FAKE CLIENT; no network")
g.TARGET_CONFIG_PATH = Path({str(spec_dir / 'provision_target.json')!r})
"""
    nb.cells.insert(0, nbformat.v4.new_code_cell(setup))
    if enter_token is not None:
        for cell in nb.cells:
            if "manual-token-entry" in cell.metadata.get("tags", []):
                # ipykernel reinstalls getpass for each cell; simulate only the
                # UI input in memory, while executing the actual token-handling code.
                cell.source = cell.source.replace("from getpass import getpass",
                    f'def getpass(prompt): return {enter_token!r}')
    if write:
        cell = nb.cells[-1]
        if provision:
            cell.source = cell.source.replace("PROVISION_ENABLED = False", "PROVISION_ENABLED = True").replace(
                'PROVISION_CONFIRMATION = ""', 'PROVISION_CONFIRMATION = "CREATE GASI FB81 PLAYGROUND TEST AREA"')
        else:
            cell.source = cell.source.replace("WRITE_ENABLED = False", "WRITE_ENABLED = True").replace(
                'WRITE_CONFIRMATION = ""', 'WRITE_CONFIRMATION = "WRITE SYNTHETIC TEST TO BAM PLAYGROUND"')
        if repeat:
            nb.cells.append(nbformat.v4.new_code_cell(cell.source))
    if fake:
        assertion = "assert len(fake.created) == 3 and fake.downloads == 2" if write else "assert not fake.created"
        if path.name == PROVISION_NOTEBOOK:
            assertion = "assert len(fake.saved) == 4 and not fake.created" if write else "assert not fake.saved and not fake.created"
        nb.cells.append(nbformat.v4.new_code_cell(assertion))
    nb.cells.append(nbformat.v4.new_code_cell("assert not network_attempts"))
    km = AsyncKernelManager(kernel_name="gasi-test", connection_file=str(spec_dir / f"connection_{path.stem}.json"),
                            kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(spec_dir)]))
    env = {**os.environ, "OPENBIS_PLAYGROUND_TOKEN": "", "IPYTHONDIR": str(spec_dir / "ipython"),
           "JUPYTER_RUNTIME_DIR": str(spec_dir)}
    client = NotebookClient(nb, km=km, resources={"metadata": {"path": str(cwd)}}, timeout=120)
    try:
        client.execute(env=env)
        for cell in nb.cells:
            assert "FAKE_SECRET_FOR_NOTEBOOK" not in json.dumps(cell.get("outputs", []))
            if path.name in NOTEBOOKS[1:3] and (cwd / "config/gasi_setup.json").is_file():
                setup = json.loads((cwd / "config/gasi_setup.json").read_text(encoding="utf-8"))
                for device in setup["devices"]:
                    serial = device.get("serial_number")
                    assert not serial or serial not in json.dumps(cell.get("outputs", []))
    finally:
        # NotebookClient does not own externally supplied managers.
        if km.has_kernel:
            import asyncio
            asyncio.run(km.shutdown_kernel(now=True))
    print(f"PASS {path.name}: {'fake write + retry' if write else 'fake read only' if fake else 'no-token Run All'}")


def check_html_notebook(base, spec_dir):
    isolated = base / "model-repo"
    (isolated / "docs").mkdir(parents=True)
    shutil.copy(ROOT / "gasi_model_html.py", isolated)
    shutil.copy(ROOT / "gasi_session.py", isolated)
    source = isolated / "docs/GaSi_Datenmodell.md"
    shutil.copy(ROOT / "docs/GaSi_Datenmodell.md", source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    execute(ROOT / "GaSi_01_Datenmodell_HTML_erzeugen.ipynb", isolated, spec_dir)
    assert digest in source.with_suffix(".html").read_text(encoding="utf-8")
    simple = source.with_name(source.stem + "_einfach.html").read_text(encoding="utf-8")
    assert 'name="gasi-view" content="simple"' in simple
    assert digest in simple and "<table>" not in simple
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    print("PASS HTML notebook: generates current source, Markdown unchanged")


def check_session_notebook(base, spec_dir):
    isolated = base / "session-repo"
    isolated.mkdir()
    shutil.copy(ROOT / "gasi_session.py", isolated)
    credentials = isolated / ".env"
    execute(ROOT / SESSION_NOTEBOOK, isolated, spec_dir,
            enter_token="FAKE_SECRET_FOR_NOTEBOOK", session_file=credentials)
    original = credentials.read_bytes()
    assert b"FAKE_SECRET_FOR_NOTEBOOK" in original
    execute(ROOT / SESSION_NOTEBOOK, isolated, spec_dir, enter_token="", session_file=credentials)
    assert credentials.read_bytes() == original
    print("PASS session notebook: hidden input, central file, fresh-kernel reuse, empty input preserves token")
    return credentials


def check_project_notebook(base, spec_dir):
    isolated = base / "project setup"
    nested = isolated / "example folder"
    nested.mkdir(parents=True)
    for name in ("requirements-dev.txt", "requirements-playground.txt", "requirements-docs.txt"):
        shutil.copy(ROOT / name, isolated)
    shutil.copy(ROOT / "gasi_session.py", nested)
    execute(ROOT / PROJECT_NOTEBOOK, nested, spec_dir, simulate_install=True)
    # Nur den Workshop-Einrichtungsabschnitt ausführen, keine Verbindung/Schreibübung.
    workshop = nbformat.read(ROOT / "example/pybis_workshop_exercises.ipynb", as_version=4)
    workshop.cells = workshop.cells[:7]
    path = nested / "workshop_environment.ipynb"
    nbformat.write(workshop, path)
    execute(path, nested, spec_dir, simulate_install=True)
    print("PASS project/workshop setup: current interpreter, nested cwd, simulated pip, real imports, no network")


def check_target_notebook(base, spec_dir):
    isolated = base / "target-repo"
    nested = isolated / "config"
    nested.mkdir(parents=True)
    for name in ("gasi_session.py", "gasi_openbis_playground.py", "gasi_playground_targets.py"):
        shutil.copy(ROOT / name, isolated)
    shutil.copy(ROOT / "config/playground_test_target.example.json", nested)
    execute(ROOT / TARGET_NOTEBOOK, isolated, spec_dir)
    path = nested / "playground_test_target.json"
    original = path.read_bytes()
    assert not json.loads(original)["approved_test_scope"]["steward_approved"]
    execute(ROOT / TARGET_NOTEBOOK, isolated, spec_dir)
    assert path.read_bytes() == original
    print("PASS target notebook: local template only, existing file preserved, no network or openBIS writes")


def main(html_only=False):
    originals = {} if html_only else {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "data/measurements").glob("*.csv")}
    runtime = ROOT / ".local_playground_test"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gasi-notebooks-", dir=runtime) as temp:
        base = Path(temp)
        spec = base / "kernels" / "gasi-test"
        spec.mkdir(parents=True)
        (spec / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "GaSi test", "language": "python",
        }), encoding="utf-8")
        if html_only:
            check_html_notebook(base, spec.parent)
            return
        check_project_notebook(base, spec.parent)
        credentials = check_session_notebook(base, spec.parent)
        check_target_notebook(base, spec.parent)
        execute(ROOT / PROVISION_NOTEBOOK, ROOT, spec.parent)
        execute(ROOT / PROVISION_NOTEBOOK, ROOT, spec.parent, fake=True)
        execute(ROOT / PROVISION_NOTEBOOK, ROOT, spec.parent, fake=True, write=True, repeat=True, provision=True)
        for path in NOTEBOOKS[1:]:
            execute(ROOT / path, ROOT, spec.parent)
        empty = base / "empty-repo"
        empty.mkdir()
        shutil.copy(ROOT / "gasi_local_measurements.py", empty)
        shutil.copy(ROOT / "gasi_setup.py", empty)
        shutil.copy(ROOT / "gasi_session.py", empty)
        execute(ROOT / NOTEBOOKS[1], empty, spec.parent)
        execute(ROOT / NOTEBOOKS[2], empty, spec.parent)
        for path in NOTEBOOKS[3:]:
            execute(ROOT / path, ROOT, spec.parent, fake=True, session_file=credentials)
        execute(ROOT / NOTEBOOKS[4], ROOT, spec.parent, fake=True, write=True, repeat=True)
        check_html_notebook(base, spec.parent)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in originals.items())
    print(f"PASS original CSV files unchanged: {len(originals)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-only", action="store_true", help="Nur das eigenständige HTML-Notebook prüfen")
    main(html_only=parser.parse_args().html_only)
