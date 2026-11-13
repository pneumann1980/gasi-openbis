"""Guided local drafts, explicit unknowns and hash-bound synthetic uploads."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace

from test_local_measurements import fixture
from test_simple_workflow import AppClient, configure
from test_inventory import fixture as inventory_fixture
from test_staged_upload import measurement_fixture, analysis_fixture, StagedClient, configuration
import gasi_run_draft as guide
import gasi_run as runs
import gasi_analysis as analysis
import gasi_openbis_playground as ob
import gasi_session as session
import gasi_workflow as app
import gasi_dut


class RunDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data/measurements').mkdir(parents=True)
        (self.root / 'config').mkdir()
        for source in guide.ROOT.glob('config/*.example.json'):
            (self.root / 'config' / source.name).write_bytes(source.read_bytes())
        self.csv = fixture(self.root / 'data/measurements', {'A5B_CH01_mV': '1,2'}, repeated_header=True)
        switch = patch.object(session, 'SESSION_FILE', self.root / '.env')
        switch.start(); self.addCleanup(switch.stop)

    def draft(self, **changes):
        args = dict(root=self.root, selections=[dict(file='data/measurements/synthetic.csv', first_record=1, last_record=1, utc_offset='+01:00')],
                    dut_id='/INVENTORY/DUT', purpose='Synthetic characterization', responsible_person='Synthetic tester', ownership='exclusive')
        args.update(changes)
        return guide.build_draft(**args)

    def test_minimal_capture_retains_unknowns_and_original_bytes(self):
        before = self.csv.read_bytes()
        draft = self.draft()
        self.assertFalse(draft['issues'])
        self.assertEqual(draft['config']['stages'], [])
        self.assertEqual(draft['config']['channels'], [])
        self.assertEqual(draft['config']['resources']['gas_sources'], [])
        self.assertFalse(draft['config']['setup_confirmed'])
        self.assertIsNone(draft['config']['software_versions']['acquisition'])
        self.assertGreater(len(draft['metadata_gaps']), 3)
        bundle = runs.prepare_bundle(draft['config'], self.root)
        context = json.loads((bundle['path'] / 'context/context.json').read_bytes())
        self.assertEqual(context['metadata_gaps'], draft['metadata_gaps'])
        self.assertEqual(context['metadata_profile'], 'raw_capture')
        self.assertEqual(self.csv.read_bytes(), before)

    def test_stable_id_and_records_ignore_repeated_headers(self):
        first, second = self.draft(), self.draft()
        self.assertEqual(first['config']['run_id'], second['config']['run_id'])
        summary = first['config']['draft_provenance']['source_observations'][0]
        self.assertEqual(summary['records'], 1)
        self.assertEqual(summary['first_local'], '2026-11-11T12:00:00')
        self.assertEqual(first['config']['times']['measurement']['start'], '2026-11-11T12:00:00+01:00')
        changed = self.draft(dut_id='/INVENTORY/OTHER_SENSOR')
        self.assertNotEqual(first['config']['run_id'], changed['config']['run_id'])

    def test_existing_described_run_keeps_recorded_context_and_run_times(self):
        base = measurement_fixture(self.root)
        base['setup_snapshot'] = dict(setup_id='SYNTHETIC_RECORDED_SETUP', configuration_sha256='a' * 64)
        dut_signal = next(c for c in base['channels'] if c['role'] == 'dut_signal')
        draft = guide.build_draft(root=self.root, selections=base['source_ranges'],
            dut_id=base['dut']['identifier'], purpose=base['purpose'], responsible_person=base['responsible_person'],
            run_id=base['run_id'], instruments=base['resources']['instruments'], ownership='exclusive',
            setup_evidence=base['setup_evidence'], acquisition_version=base['software_versions']['acquisition'],
            signal=dut_signal, base=base)
        self.assertFalse(draft['issues'])
        self.assertEqual(draft['config']['metadata_profile'], 'described_run')
        for key in ('times', 'stages', 'stage_ranges', 'channels', 'setup_snapshot'):
            self.assertEqual(draft['config'][key], base[key])

    def test_unknown_identity_time_or_shared_original_still_blocks_upload(self):
        cases = [dict(dut_id=''), dict(ownership='unknown'), dict(ownership='shared'),
                 dict(selections=[dict(file='data/measurements/synthetic.csv', utc_offset='')])]
        for changes in cases:
            with self.subTest(changes=changes):
                draft = self.draft(**changes)
                self.assertTrue(draft['issues'])
                with self.assertRaises(ob.CheckFailed): runs.prepare_bundle(draft['config'], self.root)
        shared = self.draft(ownership='shared')
        self.assertEqual(shared['config']['raw_file_policy']['shared_sources'][0]['file'], 'data/measurements/synthetic.csv')
        unassigned = self.draft()['config']
        unassigned['source_association_confirmed'] = False
        self.assertTrue(runs.validate_run(unassigned, self.root))

    def test_nan_short_rows_and_invalid_record_ranges_do_not_modify_sources(self):
        for kwargs in ({'changes': {'A5B_CH01_mV': 'NaN'}}, {'truncate': True}):
            fixture(self.root / 'data/measurements', **kwargs)
            before = self.csv.read_bytes()
            with self.assertRaises(ob.CheckFailed): self.draft()
            self.assertEqual(self.csv.read_bytes(), before)
        fixture(self.root / 'data/measurements')
        with self.assertRaises(ob.CheckFailed):
            self.draft(selections=[dict(file='data/measurements/synthetic.csv', first_record=1, last_record=9, utc_offset='+01:00')])

    def test_changed_source_after_selection_or_after_save_is_rejected(self):
        old = guide.source_summary(self.root, 'data/measurements/synthetic.csv')
        draft = self.draft()
        self.csv.write_bytes(self.csv.read_bytes().replace(b'1,2', b'2,3'))
        with self.assertRaises(ob.CheckFailed):
            self.draft(selections=[dict(file='data/measurements/synthetic.csv', utc_offset='+01:00', sha256=old['sha256'])])
        with self.assertRaises(ob.CheckFailed): runs.prepare_bundle(draft['config'], self.root)

    def test_save_keeps_previous_configuration_and_rejects_concurrent_edits(self):
        path = self.root / 'config/gasi_run.json'
        path.write_bytes(b'{"previous":"synthetic"}\n')
        old = path.read_bytes(); digest = guide.config_hash(self.root)
        draft = self.draft()
        current = guide.save_draft(draft, root=self.root, expected_hash=digest)
        backups = list((self.root / '.local_playground_test/run_drafts').glob('*/gasi_run.json'))
        self.assertEqual(backups[0].read_bytes(), old)
        path.write_bytes(b'{"newer":"synthetic edit"}\n')
        with self.assertRaises(ob.CheckFailed): guide.save_draft(draft, root=self.root, expected_hash=current)
        self.assertIn(b'newer', path.read_bytes())

    def test_form_open_and_save_stay_offline_even_with_armed_session(self):
        session.start_session(True)
        with patch.object(ob, 'connect_playground', side_effect=AssertionError('No connection in local form')), redirect_stdout(io.StringIO()):
            editor = guide.RunPreparation(self.root)
            editor.files.value = ('data/measurements/synthetic.csv',)
            editor.load_sources()
            editor.file_rows[editor.files.value[0]]['offset'].value = '+01:00'
            editor.dut.value = '/INVENTORY/DUT'
            editor.person.value = 'Synthetic tester'; editor.purpose.value = 'Synthetic run'
            editor.ownership.value = 'exclusive'
            draft = editor.save()
            self.assertFalse(draft['issues'])
            editor.purpose.value = 'Unsaved change'
            with self.assertRaises(ob.CheckFailed): editor.execute()
            editor.widget.close()

    def test_changed_ownership_and_identity_cannot_be_confirmed_by_setup_snapshot(self):
        draft = self.draft(ownership='unknown', dut_id='', setup_evidence='Synthetic setup note')
        self.assertTrue(draft['issues'])
        self.assertFalse(draft['config']['dut']['identity_confirmed'])
        self.assertFalse(draft['config']['raw_file_policy']['confirmed'])

    def test_saved_name_instead_of_identifier_explains_exact_blocker(self):
        draft = self.draft(dut_id='UNREGISTERED_SENSOR')
        self.assertFalse(draft['config']['dut']['identity_confirmed'])
        self.assertIsNone(draft['config']['run_id'])
        guide.save_draft(draft, root=self.root, expected_hash=None)
        output = io.StringIO()
        with patch.object(ob, 'connect_playground', side_effect=AssertionError('No write/read connection for invalid draft')), redirect_stdout(output):
            editor = guide.RunPreparation(self.root)
            self.assertIn('bezeichnung', editor.status.value.casefold())
            result, message = editor.execute()
            self.assertTrue(result['issues'])
            editor.widget.close()
        self.assertIn('keinem openBIS-Objekt zugeordnet', output.getvalue())
        self.assertNotIn('Zuerst Originale und Prüfling', output.getvalue())
        self.assertNotIn('Laufkennung fehlt', output.getvalue())

    def test_dut_manager_replaces_unresolved_name_and_preserves_other_canonical_identity(self):
        draft = self.draft(dut_id='UNRESOLVED_NAME')
        guide.save_draft(draft, root=self.root, expected_hash=None)
        dutpath = self.root / 'config/gasi_pruefling.json'
        dutpath.write_text(json.dumps(dict(identifier='/INVENTORY/DUT', kind='gas_humidity_sensor')), encoding='utf-8')
        row = dict(identifier='/INVENTORY/DUT', code='DUT', type='SAMPLE', props={'$name':'Synthetic sensor'})
        with patch('gasi_session.writes_enabled', return_value=True), \
             patch.object(ob, 'load_target_config', return_value=({}, 'Synthetic')), \
             patch.object(ob, 'connect_playground', return_value=(object(), 'Synthetic')), \
             patch.object(gasi_dut, 'ensure_dut', return_value=(row, False)):
            result, message = gasi_dut.manage_dut(self.root)
            self.assertTrue(result.get('pruefling'), message)
            runpath = self.root / 'config/gasi_run.json'
            saved = json.loads(runpath.read_bytes())
            self.assertEqual(saved['dut']['identifier'], '/INVENTORY/DUT')
            saved['dut']['identifier'] = '/INVENTORY/OTHER'
            runpath.write_text(json.dumps(saved), encoding='utf-8')
            gasi_dut.manage_dut(self.root)
            self.assertEqual(json.loads(runpath.read_bytes())['dut']['identifier'], '/INVENTORY/OTHER')
            saved['measurement_subject'] = 'unresolved'
            saved['dut']['identifier'] = None
            runpath.write_text(json.dumps(saved), encoding='utf-8')
            gasi_dut.manage_dut(self.root)
            self.assertIsNone(json.loads(runpath.read_bytes())['dut']['identifier'])

    def test_resolved_search_selection_generates_run_id_after_save(self):
        draft = self.draft(dut_id='SENSOR_LABEL')
        guide.save_draft(draft, root=self.root, expected_hash=None)
        with redirect_stdout(io.StringIO()):
            editor = guide.RunPreparation(self.root)
            matches = [dict(identifier='/INVENTORY/DUT', name='Synthetic sensor', type='SAMPLE')]
            with patch.object(gasi_dut, 'find_duts', return_value=(matches, 'Synthetic read only')):
                editor.search_dut()
            self.assertEqual(editor.dut.value, '/INVENTORY/DUT')
            self.assertIn('nicht gespeichert', editor.status.value)
            saved = editor.save()
            self.assertFalse(saved['issues'])
            self.assertTrue(saved['config']['run_id'])
            self.assertTrue(saved['config']['dut']['identity_confirmed'])
            self.assertIn('Mindestangaben', editor.status.value)
            editor.widget.close()

    def test_dut_lookup_accepts_name_permid_and_browser_link_but_never_creates(self):
        row = dict(identifier='/INVENTORY/DUT', code='DUT', type='SAMPLE', permId='20261113120000000-1', props={'$name':'Synthetic sensor'})
        client = SimpleNamespace(url=ob.PLAYGROUND_HOST, get_samples=Mock(return_value=[row]), get_sample=Mock(return_value=row),
                                 new_sample=Mock(side_effect=AssertionError('No creation in lookup')))
        for query in ('Synthetic sensor', '20261113120000000-1', '/INVENTORY/DUT',
                      ob.PLAYGROUND_HOST + '/openbis/webapp/eln-lims/?viewName=showViewSamplePageFromPermId&viewData=20261113120000000-1'):
            found, message = gasi_dut.find_duts(query, client)
            self.assertEqual([v['identifier'] for v in found], ['/INVENTORY/DUT'], message)
        self.assertFalse(client.new_sample.called)
        self.assertFalse(gasi_dut.find_duts('Not registered', client)[0])
        client.url = 'https://production.invalid'
        self.assertFalse(gasi_dut.find_duts('Synthetic sensor', client)[0])
        client.url = ob.PLAYGROUND_HOST
        client.get_samples.side_effect = RuntimeError('SECRET_FAKE_TOKEN')
        found, message = gasi_dut.find_duts('Synthetic sensor', client)
        self.assertFalse(found)
        self.assertNotIn('SECRET_FAKE_TOKEN', message)

    def test_system_and_unresolved_recordings_need_no_invented_sensor(self):
        for subject in ('system', 'unresolved'):
            draft = self.draft(dut_id='', measurement_subject=subject)
            self.assertFalse(draft['issues'])
            self.assertTrue(draft['config']['run_id'])
            self.assertIsNone(draft['config']['dut']['identifier'])
            self.assertFalse(draft['config']['dut']['identity_confirmed'])
            self.assertEqual(draft['config']['channels'], [])
            self.assertEqual(draft['config']['measurement_subject'], subject)
            self.assertEqual(draft['config']['run_id'], self.draft(dut_id='', measurement_subject=subject)['config']['run_id'])
            self.assertEqual(any('Prüflingsbezug ungeklärt' in s for s in draft['metadata_gaps']), subject == 'unresolved')
        wrong = self.draft(dut_id='', measurement_subject='system')['config']
        wrong['dut'].update(identifier='/INVENTORY/DUT', identity_confirmed=True)
        self.assertTrue(runs.validate_run(wrong, self.root))

    def test_system_recording_upload_repeat_and_analysis_keep_subject_unknown(self):
        draft = self.draft(dut_id='', measurement_subject='unresolved', subject_evidence='Synthetic uncertainty')
        client = StagedClient()
        targets = configuration()
        bundle = runs.prepare_bundle(draft['config'], self.root)
        client.fail_after = 'dataset'
        with self.assertRaises(TimeoutError): runs.ensure_workflow(client, bundle, targets)
        result = runs.ensure_workflow(client, bundle, targets)
        measurement = client.get_sample(result['objects']['measurement']['identifier'])
        self.assertEqual(list(ob.records(measurement.get_parents())), [])
        self.assertIsNone(result['dut']['identifier'])
        self.assertIn('Anlagenaufzeichnung', ob.name(measurement))
        count = len(client.created)
        runs.ensure_workflow(client, bundle, targets)
        self.assertEqual(len(client.created), count)
        self.assertFalse(any(code.startswith('GASI_DUT_') for code in client.created))
        (self.root / 'data/results').mkdir()
        (self.root / 'data/results/result.csv').write_text('synthetic\n1\n', encoding='utf-8')
        config = analysis_fixture(result)
        verified = analysis.ensure_analysis(client, analysis.prepare_analysis(config, self.root), targets)
        self.assertEqual(verified['inputs'][0]['recorded_measurement_subject'], 'unresolved')

    def test_form_can_save_uncertain_subject_without_sensor_search(self):
        with redirect_stdout(io.StringIO()):
            editor = guide.RunPreparation(self.root)
            editor.files.value = ('data/measurements/synthetic.csv',)
            editor.load_sources()
            editor.file_rows[editor.files.value[0]]['offset'].value = '+01:00'
            editor.subject.value = 'unresolved'
            editor.subject_note.value = 'No reliable sensor association supplied'
            self.assertTrue(editor.dut.disabled)
            self.assertTrue(editor.search_button.disabled)
            editor.person.value = 'Synthetic tester'; editor.purpose.value = 'Plant recording'
            editor.ownership.value = 'exclusive'
            saved = editor.save()
            self.assertFalse(saved['issues'])
            self.assertIsNone(saved['config']['dut']['identifier'])
            self.assertIn('Mindestangaben', editor.status.value)
            editor.widget.close()

    def test_minimal_capture_resume_repeat_and_later_analysis_without_invented_stages(self):
        root = self.root / 'integration'
        inventory_fixture(root)
        client = AppClient(); configure(root, client)
        original = measurement_fixture(root)
        session.start_session(True)
        with patch.object(ob, 'connect_playground', return_value=(client, 'Synthetic')):
            _, message = app.setup_project(root)
        self.assertIn('bestätigt', message)
        draft = guide.build_draft(root=root, selections=original['source_ranges'], dut_id=original['dut']['identifier'],
                   purpose='Synthetic capture', responsible_person='Synthetic tester', ownership='exclusive')
        self.assertFalse(draft['issues'])
        bundle = runs.prepare_bundle(draft['config'], root)
        targets = ob.load_target_config(root / 'config/playground_test_target.json')[0]
        client.fail_after = 'dataset'
        with self.assertRaises(TimeoutError): runs.ensure_workflow(client, bundle, targets)
        result = runs.ensure_workflow(client, bundle, targets)
        measurement = client.get_sample(result['objects']['measurement']['identifier'])
        self.assertIn('Rohdatenerfassung', ob.name(measurement))
        count = len(client.created)
        runs.ensure_workflow(client, bundle, targets)
        self.assertEqual(len(client.created), count)
        receipt = next(d for d in client.datasets.values() if d['filename'] == 'source_receipt.json')
        self.assertTrue(json.loads(receipt['bytes'])['metadata_gaps'])
        config = analysis_fixture(result)
        self.assertEqual(config['inputs'][0]['stage_ranges'], [])
        prepared = analysis.prepare_analysis(config, root)
        verified = analysis.ensure_analysis(client, prepared, targets)
        self.assertTrue(verified['inputs'][0]['recorded_metadata_gaps'])
        self.assertEqual(verified['inputs'][0]['sha256'], draft['config']['source_file_sha256'][original['files']['raw_data'][0]])
