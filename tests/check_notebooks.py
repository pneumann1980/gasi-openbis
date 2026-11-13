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
INVENTORY_NOTEBOOKS = ("GaSi_06_Geraetezuordnung_pruefen.ipynb", "GaSi_07_Geraeteinventar_anlegen.ipynb")
RESEARCH_NOTEBOOK = "GaSi_08_Forschungsablauf_hochladen.ipynb"
ANALYSIS_NOTEBOOK = "GaSi_09_Auswertung_hochladen.ipynb"
NOTEBOOKS = ("GaSi_01_Datenmodell_HTML_erzeugen.ipynb", "GaSi_02_Aktuelles_Setup_pruefen.ipynb",
             "GaSi_03_Messdateien_pruefen.ipynb", "GaSi_04_Playground_Bestand_lesen.ipynb", "GaSi_05_Playground_Schreibtest.ipynb")


def execute(path, cwd, spec_dir, *, fake=False, write=False, repeat=False, enter_token=None, session_file=None, simulate_install=False, provision=False, inventory=False, research=False):
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
        if path.name in (RESEARCH_NOTEBOOK,ANALYSIS_NOTEBOOK):
            setup += """
from test_staged_upload import StagedClient, measurement_fixture, analysis_fixture
from test_research_workflow import configuration
import gasi_run
fake = StagedClient()
g.connect_playground = lambda: (fake, "LOCAL FAKE CLIENT; no network")
g.load_target_config = lambda path=None: (configuration(), "LOCAL FAKE WORKFLOW CONFIG")
"""
        if path.name == ANALYSIS_NOTEBOOK:
            setup += """
run = measurement_fixture(Path.cwd())
captured = gasi_run.ensure_workflow(fake, gasi_run.prepare_bundle(run), configuration())
import json
Path("config/gasi_analysis.json").write_text(json.dumps(analysis_fixture(captured)), encoding="utf-8")
"""
        if path.name == PROVISION_NOTEBOOK:
            setup += f"""
from test_playground_provision import ProvisionClient
fake = ProvisionClient()
g.connect_playground = lambda: (fake, "LOCAL FAKE CLIENT; no network")
g.TARGET_CONFIG_PATH = Path({str(spec_dir / 'provision_target.json')!r})
"""
        if path.name == INVENTORY_NOTEBOOKS[1]:
            setup += """
from test_inventory import InventoryClient
import gasi_inventory_openbis as inventory_module
fake = InventoryClient()
inventory_settings = inventory_module.default_settings()
inventory_settings["authorization"]["reference"] = "EXPLICIT FAKE NOTEBOOK AUTHORIZATION"
inventory_settings["location"] = dict(code="TEST_EXISTING_LOCATION", confirmed=True, evidence="Synthetic room fixture")
inventory_module.load_inventory_settings = lambda: (inventory_settings, "LOCAL FAKE INVENTORY SETTINGS")
g.connect_playground = lambda: (fake, "LOCAL FAKE CLIENT; no network")
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
        if research:
            phrase = "UPLOAD GASI ANALYSIS TO PLAYGROUND" if path.name==ANALYSIS_NOTEBOOK else "UPLOAD CONFIGURED GASI RESEARCH WORKFLOW TO PLAYGROUND"
            cell.source = cell.source.replace("UPLOAD_ENABLED = False", "UPLOAD_ENABLED = True").replace(
                'CONFIRMATION = ""', f'CONFIRMATION = "{phrase}"')
        elif inventory:
            cell.source = cell.source.replace("REGISTER_ENABLED = False", "REGISTER_ENABLED = True").replace(
                'REGISTER_CONFIRMATION = ""', 'REGISTER_CONFIRMATION = "REGISTER DOCUMENTED GASI DEVICE IDENTITIES ON PLAYGROUND"')
        elif provision:
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
        if path.name == INVENTORY_NOTEBOOKS[1]:
            assertion = "assert len(fake.created) == 1 and len(fake.saved) == 2" if write else "assert not fake.created and not fake.saved"
        if path.name == RESEARCH_NOTEBOOK:
            assertion = "assert len(fake.created) == 5 and len(fake.datasets) == 4 and len(fake.samples) == 4" if write else "assert not fake.created"
        if path.name == ANALYSIS_NOTEBOOK:
            assertion = "assert len(fake.created) == 8 and len(fake.datasets) == 6" if write else "assert len(fake.created) == 5"
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
            if path.name in (*NOTEBOOKS[1:3], *INVENTORY_NOTEBOOKS) and (cwd / "config/gasi_setup.json").is_file():
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
    shutil.copy(ROOT / "gasi_concept_html.py", isolated)
    shutil.copy(ROOT / "gasi_session.py", isolated)
    source = isolated / "docs/GaSi_Datenmodell.md"
    shutil.copy(ROOT / "docs/GaSi_Datenmodell.md", source)
    concept = isolated / "docs/GaSi_Konzeptmodell.md"
    shutil.copy(ROOT / "docs/GaSi_Konzeptmodell.md", concept)
    concept_digest = hashlib.sha256(concept.read_bytes()).hexdigest()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    execute(ROOT / "GaSi_01_Datenmodell_HTML_erzeugen.ipynb", isolated, spec_dir)
    assert digest in source.with_suffix(".html").read_text(encoding="utf-8")
    simple = source.with_name(source.stem + "_einfach.html").read_text(encoding="utf-8")
    assert 'name="gasi-view" content="simple"' in simple
    assert digest in simple and "<table>" not in simple
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    assert concept_digest in concept.with_suffix(".html").read_text(encoding="utf-8")
    assert 'href="GaSi_Konzeptmodell.html"' in simple
    assert hashlib.sha256(concept.read_bytes()).hexdigest() == concept_digest
    assert len(list(isolated.glob("docs/GaSi_Konzeptmodell_*.svg"))) == 4
    print("PASS HTML notebook: both current sources, four BAM steps, four SVGs, Markdown unchanged")


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


def check_inventory_notebooks(base, spec_dir):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    from test_inventory import fixture
    isolated = base / "inventory-repo"
    fixture(isolated)
    for name in ("gasi_session.py", "gasi_openbis_playground.py", "gasi_inventory.py", "gasi_inventory_openbis.py",
                 "gasi_playground_targets.py", "gasi_playground_provision.py", "gasi_local_measurements.py", "gasi_setup.py"):
        shutil.copy(ROOT / name, isolated)
    shutil.copy(ROOT / "config/playground_test_target.example.json", isolated / "config")
    source = isolated / "data/datasheets/test_Inventar.csv"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    execute(ROOT / INVENTORY_NOTEBOOKS[0], isolated, spec_dir)
    execute(ROOT / INVENTORY_NOTEBOOKS[1], isolated, spec_dir)
    execute(ROOT / INVENTORY_NOTEBOOKS[1], isolated, spec_dir, fake=True)
    execute(ROOT / INVENTORY_NOTEBOOKS[1], isolated, spec_dir, fake=True, write=True, repeat=True, inventory=True)
    empty = base / "inventory-empty"
    empty.mkdir()
    for name in ("gasi_session.py", "gasi_inventory.py"):
        shutil.copy(ROOT / name, empty)
    execute(ROOT / INVENTORY_NOTEBOOKS[0], empty, spec_dir)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    print("PASS inventory notebooks: offline identity check, empty folder, read-only preview, metadata registration/retry, asset source unchanged")


def check_research_notebook(base,spec_dir):
    isolated=base / "research-repo"
    (isolated/"config").mkdir(parents=True)
    for name in ("gasi_run.py","gasi_analysis.py","gasi_local_measurements.py","gasi_openbis_playground.py","gasi_session.py"):
        shutil.copy(ROOT/name,isolated)
    for name in ("gasi_run.example.json","gasi_analysis.example.json","playground_test_target.example.json"):
        shutil.copy(ROOT/"config"/name,isolated/"config")
    execute(ROOT/RESEARCH_NOTEBOOK,isolated,spec_dir)
    sys.path.insert(0,str(ROOT))
    from tests.test_staged_upload import measurement_fixture
    run=measurement_fixture(isolated)
    (isolated/"config/gasi_run.json").write_text(json.dumps(run),encoding="utf-8")
    source=isolated/"data/measurements/synthetic.csv"
    original=source.read_bytes()
    execute(ROOT/RESEARCH_NOTEBOOK,isolated,spec_dir,fake=True)
    execute(ROOT/RESEARCH_NOTEBOOK,isolated,spec_dir,fake=True,write=True,repeat=True,research=True)
    execute(ROOT/ANALYSIS_NOTEBOOK,isolated,spec_dir)
    execute(ROOT/ANALYSIS_NOTEBOOK,isolated,spec_dir,fake=True)
    execute(ROOT/ANALYSIS_NOTEBOOK,isolated,spec_dir,fake=True,write=True,repeat=True,research=True)
    assert source.read_bytes()==original
    print("PASS staged notebooks: independent capture, later analysis, previews, retries, raw CSV unchanged")


def main(html_only=False, inventory_only=False, research_only=False):
    originals = {} if html_only or inventory_only or research_only else {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "data/measurements").glob("*.csv")}
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
        if inventory_only:
            check_inventory_notebooks(base, spec.parent)
            return
        if research_only:
            check_research_notebook(base,spec.parent)
            return
        check_project_notebook(base, spec.parent)
        credentials = check_session_notebook(base, spec.parent)
        check_target_notebook(base, spec.parent)
        check_inventory_notebooks(base, spec.parent)
        check_research_notebook(base,spec.parent)
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
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--html-only", action="store_true", help="Nur das eigenständige HTML-Notebook prüfen")
    group.add_argument("--inventory-only", action="store_true", help="Nur Gerätevorbereitung und -registrierung mit frischen Kernels prüfen")
    group.add_argument("--research-only", action="store_true", help="Nur den vollständigen Forschungsupload mit Testclient und frischen Kernels prüfen")
    args = parser.parse_args()
    main(html_only=args.html_only, inventory_only=args.inventory_only, research_only=args.research_only)
