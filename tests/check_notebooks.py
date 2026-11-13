"""Fresh-kernel acceptance of the three main notebooks, DUT and optional analysis.

Network is blocked. pip installation is simulated, package imports are real.
openBIS writes use only synthetic clients in isolated copies of the repository.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile

from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
import nbformat

ROOT = Path(__file__).resolve().parents[1]
SESSION = 'GaSi_01_Session_starten.ipynb'
SETUP = 'GaSi_02_Einmalig_einrichten.ipynb'
MEASUREMENT = 'GaSi_03_Messdaten_hochladen.ipynb'
DUT = 'GaSi_Pruefling_verwalten.ipynb'
ANALYSIS = 'notebooks/GaSi_Auswertung_hochladen.ipynb'


def copy_repo(path):
    path.mkdir()
    for name in ('config', 'docs', 'data/measurements', 'data/results'):
        (path / name).mkdir(parents=True, exist_ok=True)
    for source in ROOT.glob('gasi*.py'):
        shutil.copy2(source, path)
    for source in ROOT.glob('requirements*.txt'):
        shutil.copy2(source, path)
    for source in (ROOT / 'config').glob('*.example.json'):
        shutil.copy2(source, path / 'config')
    for source in (ROOT / 'docs').glob('*.md'):
        shutil.copy2(source, path / 'docs')


def execute(name, cwd, spec_dir, *, write=False, fake=False, repeat=False):
    nb = nbformat.read(ROOT / name, as_version=4)
    nbformat.validate(nb)
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs, cell.execution_count = [], None
            if 'install-requirements' in cell.metadata.get('tags', []):
                cell.source = cell.source.replace('subprocess.run(', '_simulate_pip(')
            if name == SESSION and write:
                cell.source = cell.source.replace('SCHREIBEN = False', 'SCHREIBEN = True')
            if name == SESSION:
                # ipykernel replaces getpass between cells; stub only this in-memory test copy.
                cell.source = cell.source.replace('from getpass import getpass',
                    'getpass = lambda prompt: "SYNTHETIC_NOTEBOOK_TOKEN"')
    preamble = f'''
import socket, os, sys, subprocess
from pathlib import Path
sys.path.insert(0, {str(cwd)!r})
sys.path.insert(1, {str(ROOT / 'tests')!r})
network_attempts = []
def forbid_network(*args, **kwargs):
    network_attempts.append(True)
    raise AssertionError("External network forbidden")
socket.create_connection = forbid_network
socket.socket.connect = forbid_network
import gasi_session as session
session.SESSION_FILE = Path({str(cwd / '.env')!r})
os.environ.pop(session.TOKEN_ENV, None)
session.start_session({write!r})
pip_calls = []
def _simulate_pip(args, **kwargs):
    assert args[:5] == [sys.executable, "-m", "pip", "install", "-r"]
    assert Path(args[5]).name == "requirements-dev.txt"
    assert Path(args[5]).is_file() and kwargs == {{"check": True}}
    pip_calls.append(args)
    return subprocess.CompletedProcess(args, 0)
import gasi_openbis_playground as ob
ob.connect_playground = lambda: (None, "No synthetic token configured")
'''
    if fake:
        preamble += '''
from unittest.mock import patch
from test_simple_workflow import AppClient, configure
from test_inventory import fixture as inventory_fixture
from test_staged_upload import measurement_fixture, analysis_fixture
import gasi_workflow as app
import gasi_dut as dut
import json
root = Path.cwd()
# Synthetic evidence only; never copy private data into this isolated repository.
(root / 'config').rmdir() if not any((root / 'config').iterdir()) else None
'''
        # Inventory fixture creates config itself; preserve the template copies.
        preamble += '''
import tempfile, shutil
with tempfile.TemporaryDirectory() as temp:
    evidence_root = Path(temp)
    inventory_fixture(evidence_root)
    shutil.copytree(evidence_root / 'data/datasheets', root / 'data/datasheets')
    shutil.copy2(evidence_root / 'config/gasi_setup.json', root / 'config/gasi_setup.json')
client = AppClient()
configure(root, client)
ob.connect_playground = lambda: (client, "Synthetic client")
'''
        if name != SETUP:
            preamble += '''
session.start_session(True)
_, setup_message = app.setup_project(root)
assert "bestätigt" in setup_message, setup_message
run = measurement_fixture(root)
(root / 'config/gasi_run.json').write_text(json.dumps(run), encoding='utf-8')
'''
        if name == DUT:
            preamble += '''
sensor = dict(identifier=None, local_id='SYNTHETIC-NOTEBOOK-SENSOR', name='Synthetic sensor', type='SAMPLE', kind='gas_humidity_sensor', properties={})
(root / 'config/gasi_pruefling.json').write_text(json.dumps(sensor), encoding='utf-8')
'''
        if name == ANALYSIS:
            preamble += '''
captured, message = app.upload_measurement(root)
assert captured.get('verification'), message
analysis = analysis_fixture(captured['verification'])
(root / 'config/gasi_analysis.json').write_text(json.dumps(analysis), encoding='utf-8')
'''
        preamble += f'''
session.start_session({write!r})
before = len(client.saved), len(client.created)
originals = {{p: p.read_bytes() for p in (root / 'data/measurements').glob('*.csv')}}
'''
    nb.cells.insert(0, nbformat.v4.new_code_cell(preamble))
    assertions = f'assert session.writes_enabled() is {write!r}\nassert not network_attempts\n'
    if name == SESSION:
        assertions += "assert session.session_value(session.TOKEN_ENV) == 'SYNTHETIC_NOTEBOOK_TOKEN'\nassert 'token' not in globals()\n"
    if name == SETUP:
        assertions += "assert len(pip_calls) == 1\nassert Path('docs/GaSi_Konzeptmodell.html').is_file()\nassert Path('docs/GaSi_Datenmodell.html').is_file()\nassert not Path('docs/GaSi_Datenmodell_einfach.html').exists()\nassert len(list(Path('docs').glob('GaSi_Konzeptmodell_*.svg'))) == 4\n"
    if fake:
        assertions += 'assert all(p.read_bytes() == content for p, content in originals.items())\n' if name != SETUP else ''
        if not write:
            assertions += 'assert before == (len(client.saved), len(client.created))\n'
        if write and name in (SETUP, MEASUREMENT, DUT, ANALYSIS):
            assertions += "assert result, message\n"
        if repeat:
            method = {SETUP:'app.setup_project(root)', MEASUREMENT:'app.upload_measurement(root)', DUT:'dut.manage_dut(root)',
                      ANALYSIS:'gasi_analysis.upload_analysis(expected_manifest_sha=preview_sha256, root=root)'}[name]
            assertions += f'counts = len(client.saved), len(client.created)\nagain, message = {method}\nassert again, message\nassert counts == (len(client.saved), len(client.created))\n'
    nb.cells.append(nbformat.v4.new_code_cell(assertions))
    class KernelManager(AsyncKernelManager):
        def __init__(self, **kwargs):
            kwargs['kernel_spec_manager'] = KernelSpecManager(kernel_dirs=[str(spec_dir)])
            super().__init__(**kwargs)
    client = NotebookClient(nb, timeout=180, kernel_name='gasi-test', kernel_manager_class=KernelManager,
                            resources={'metadata': {'path': str(cwd)}})
    client.execute()
    if name == SESSION:
        output = ''.join(item.get('text', '') for cell in nb.cells if cell.cell_type == 'code' for item in cell.outputs)
        assert 'SYNTHETIC_NOTEBOOK_TOKEN' not in output
    print('PASS', name, 'synthetic' if fake else 'empty/default', 'write' if write else 'preview', flush=True)


def main():
    originals = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'data/measurements').glob('*.csv')}
    runtime = ROOT / '.local_playground_test'
    runtime.mkdir(exist_ok=True)
    scenarios = [(SESSION, False, False), (SESSION, True, False),
                 (SETUP, False, False), (SETUP, False, True), (SETUP, True, True),
                 (MEASUREMENT, False, False), (MEASUREMENT, False, True), (MEASUREMENT, True, True),
                 (DUT, False, False), (DUT, False, True), (DUT, True, True),
                 (ANALYSIS, False, False), (ANALYSIS, False, True), (ANALYSIS, True, True)]
    with tempfile.TemporaryDirectory(prefix='simple-notebooks-', dir=runtime) as temp:
        base = Path(temp)
        spec = base / 'kernels/gasi-test'
        spec.mkdir(parents=True)
        (spec / 'kernel.json').write_text(json.dumps(dict(argv=[sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            display_name='GaSi test', language='python')), encoding='utf-8')
        for index, (name, write, fake) in enumerate(scenarios):
            cwd = base / str(index)
            copy_repo(cwd)
            execute(name, cwd, spec.parent, write=write, fake=fake, repeat=write and fake)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in originals.items())
    print(f'PASS: 5 notebooks, 14 fresh kernels; {len(originals)} original CSVs unchanged.')


if __name__ == '__main__':
    main()
