"""Provisioning recovers partial saves without duplicating targets or masterdata."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch

from pybis.entity_type import ExperimentType
from test_playground import FakeClient, things
import gasi_openbis_playground as g
import gasi_playground_provision as p


class ProvisionClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.cfg = p.proposed_config("8.1_TESTUSER", "EXPLICIT LOCAL TEST AUTHORIZATION", "TEST_EXISTING_LOCATION", "Existing test value")
        self.projects, self.collections = {}, {}
        self.location_terms = {"TEST_EXISTING_LOCATION": dict(code="TEST_EXISTING_LOCATION", label="Existing test value")}
        self.saved, self.fail_after = [], None
        for entity in (self.types["INSTRUMENT"], self.types["TESTING_EQUIPMENT"]):
            entity.data["propertyAssignments"].append(dict(propertyType=dict(code="DESCRIPTION", dataType="VARCHAR"),
                mandatory=False, plugin=None, registrationDate=None, showInEditView=True))
        assignments = [dict(propertyType=dict(code=key, dataType="VARCHAR"), mandatory=False,
            plugin=None, registrationDate=None, showInEditView=True) for key in ("$NAME", "$DEFAULT_OBJECT_TYPE")]
        self.types["COLLECTION"] = ExperimentType(self, data=dict(code="COLLECTION", propertyAssignments=assignments))
        # Actual type uses BAM_* vocabulary codes; test those exact associations.
        for a in self.types["INSTRUMENT"].data["propertyAssignments"]:
            if a["propertyType"]["code"] in ("BAM_OE", "BAM_LOCATION_COMPLETE"):
                a["propertyType"]["vocabulary"] = a["propertyType"]["code"]

    def get_experiment_type(self, type):
        return self.types[type]

    def get_terms(self, *, vocabulary):
        if vocabulary == "BAM_OE":
            return things([dict(code="OE_8.1", label="8.1")])
        if vocabulary == "BAM_LOCATION_COMPLETE":
            return things(list(self.location_terms.values()))
        return super().get_terms(vocabulary=vocabulary)

    def get_vocabulary(self, vocab):
        if vocab in ("BAM_OE", "BAM_LOCATION_COMPLETE"):
            return NS(code=vocab)
        return super().get_vocabulary(vocab)

    def get_projects(self, space=None, code=None):
        return things([NS(**data) for data in self.projects.values()
                       if (space is None or data["space"] == space) and (code is None or data["code"] == code)])

    def get_experiments(self, project=None, code=None, props=None):
        return things([NS(**data) for data in self.collections.values()
                       if (project is None or data["project"] == project) and (code is None or data["code"] == code)])

    def get_experiment(self, path):
        return NS(**self.collections[path])

    def _action(self, store, key, data):
        def save():
            if key in store:
                raise AssertionError("Duplicate creation")
            store[key] = deepcopy(data)
            self.saved.append(key)
            if self.fail_after == key:
                self.fail_after = None
                raise TimeoutError("SECRET lost-response simulation")
        return NS(save=save)

    def new_project(self, *, space, code, description):
        path = f"/{space}/{code}"
        return self._action(self.projects, path,
            dict(identifier=path, space=space, code=code, description=description))

    def new_experiment(self, *, type, code, project, props):
        self.check_props(type, props)
        path = project + "/" + code
        return self._action(self.collections, path,
            dict(identifier=path, code=code, project=project, type=type, props=props))

    def new_term(self, **kwargs):
        raise AssertionError("No global vocabulary mutation")


class ProvisionTests(unittest.TestCase):
    def test_reprovisioning_preserves_separate_real_inventory_configuration(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "target.json"
            current = deepcopy(self.cfg)
            real = dict(target=dict(space="8.1_EQUIPMENT", project="GASI", collection="INSTRUMENTS"),
                        location=dict(code="REAL-PLACE", confirmed=True, evidence="USER ROOM CONFIRMATION"))
            current["gasi_inventory"] = real
            path.write_text(json.dumps(current), encoding="utf-8")
            with patch.object(g, "connect_playground", return_value=(self.client, "FAKE")):
                result, _ = p.provision_playground(self.cfg, p.CONFIRMATION, path)
            self.assertIsNotNone(result)
            self.assertEqual(json.loads(path.read_text())["gasi_inventory"], real)

    def setUp(self):
        self.client = ProvisionClient()
        self.cfg = self.client.cfg

    def run_provision(self):
        return p.ensure_test_area(self.client, self.cfg, p.CONFIRMATION)

    def test_full_creation_readback_then_repeat_creates_nothing(self):
        result = self.run_provision()
        self.assertEqual(len(result["created"]), 4)
        self.assertTrue(g.check_write_target(g.discover_playground(self.client, self.cfg), self.cfg)["ready"])
        self.assertEqual(self.run_provision()["created"], [])
        self.assertEqual(len(self.client.saved), 4)

    def test_resume_after_each_committed_save_uses_existing_entries(self):
        keys = ["/8.1_TESTUSER/GASI_TEST", "/8.1_TESTUSER/GASI_TEST/RUNS",
                "/8.1_EQUIPMENT/GASI_TEST", "/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS"]
        for key in keys:
            with self.subTest(key=key):
                self.client = ProvisionClient()
                self.client.fail_after = key
                with self.assertRaises(TimeoutError):
                    self.run_provision()
                self.run_provision()
                self.assertEqual(len(self.client.saved), 4)
                self.assertEqual(len(set(self.client.saved)), 4)

    def test_default_preview_never_connects_or_saves(self):
        with patch.object(g, "connect_playground", side_effect=AssertionError("No network")):
            result, message = p.provision_playground(self.cfg)
        self.assertIsNone(result)
        self.assertIn("deaktiviert", message)
        self.assertEqual(self.client.saved, [])

    def test_foreign_host_scope_and_missing_authorization_block_before_save(self):
        for change in ("host", "scope", "approval"):
            with self.subTest(change=change):
                self.client = ProvisionClient()
                cfg = deepcopy(self.cfg)
                if change == "host":
                    self.client.url = "https://production.example.org"
                elif change == "scope":
                    cfg["inventory"]["space"] = "7.2_EQUIPMENT"
                else:
                    cfg["approved_test_scope"]["steward_approved"] = False
                with self.assertRaises(g.CheckFailed):
                    p.ensure_test_area(self.client, cfg, p.CONFIRMATION)
                self.assertEqual(self.client.saved, [])

    def test_unmarked_existing_project_is_never_reused_or_modified(self):
        path = "/8.1_EQUIPMENT/GASI_TEST"
        self.client.projects[path] = dict(identifier=path, space="8.1_EQUIPMENT", code="GASI_TEST",
                                          description="Foreign project")
        with self.assertRaises(g.CheckFailed):
            self.run_provision()
        self.assertEqual(self.client.saved, [])

    def test_local_config_saved_only_after_success_and_errors_hide_server_details(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "target.json"
            self.client.fail_after = "/8.1_TESTUSER/GASI_TEST"
            with patch.object(g, "connect_playground", return_value=(self.client, "FAKE")):
                result, message = p.provision_playground(self.cfg, p.CONFIRMATION, path)
                self.assertIsNone(result)
                self.assertNotIn("SECRET", message)
                self.assertFalse(path.exists())
                result, _ = p.provision_playground(self.cfg, p.CONFIRMATION, path)
                self.assertTrue(path.exists())
                self.assertIsNotNone(result)
