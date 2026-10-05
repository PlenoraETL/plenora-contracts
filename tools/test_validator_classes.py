"""Regression probes for defect classes of the validator: lookups that ignore
the operation version, null members read as absent (or as present), JSON
objects with repeated keys, indexes that overwrite an entry in silence and
nulls that crash the gate instead of failing it.

Each probe breaks one document in memory and expects an explicit failure.
"""

import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/runtime-v1"


def vector(name):
    return validator.load_json(VECTORS / name)


class RestBoundaryVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validator.load_catalogs()[validator.REST_COMPONENT]
        cls.request = validator.load_json(ROOT / "examples/valid/rest-runtime-artifact-request.json")

    def errors(self, change):
        document = copy.deepcopy(self.request)
        change(document)
        return validator.rest_boundary_errors(document, self.catalog)

    def test_valid_request_conforms(self):
        self.assertEqual(validator.rest_boundary_errors(self.request, self.catalog), [])

    def test_unknown_version_is_rejected_with_a_single_catalog_version(self):
        errors = self.errors(lambda doc: doc.update(version=99))
        self.assertTrue(any("unknown runtime operation" in error for error in errors), errors)

    def test_missing_version_is_rejected(self):
        for name, change in [
            ("absent", lambda doc: doc.pop("version")),
            ("null", lambda doc: doc.update(version=None)),
            ("text", lambda doc: doc.update(version="1")),
            ("boolean", lambda doc: doc.update(version=True)),
        ]:
            with self.subTest(case=name):
                errors = self.errors(change)
                self.assertTrue(any("operation version" in error for error in errors), errors)


class NullMemberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = validator.load_catalogs()
        cls.rest = cls.catalogs[validator.REST_COMPONENT]
        cls.request = validator.load_json(ROOT / "examples/valid/rest-runtime-artifact-request.json")
        cls.storage = {
            (item["id"], item["version"]): item
            for item in cls.catalogs[validator.STORAGE_COMPONENT]["operations"]
        }

    def rest_errors(self, change):
        document = copy.deepcopy(self.request)
        change(document)
        return validator.rest_boundary_errors(document, self.rest)

    def test_null_upload_source_is_not_a_source(self):
        errors = self.rest_errors(lambda doc: doc["input"].update(artifact_source=None))
        self.assertTrue(any("requires artifact_source" in error for error in errors), errors)

    def test_null_forbidden_rest_artifact_is_still_forbidden(self):
        errors = self.rest_errors(lambda doc: doc["input"].update(artifact_sink=None))
        self.assertTrue(any("forbids artifact_sink" in error for error in errors), errors)

    def test_null_forbidden_storage_artifacts_are_still_forbidden(self):
        for name, member, reason in [
            ("storage-get-request.json", "artifact_source", "storage.get forbids artifact_source"),
            ("storage-put-request.json", "artifact_sink", "storage.put forbids artifact_sink"),
        ]:
            with self.subTest(vector=name):
                document = vector(name)
                document["payload"][member] = None
                operation = self.storage[(document["metadata"]["plenora.capability.operation"], 1)]
                errors = validator.storage_vector_errors(document, operation)
                self.assertIn(reason, errors)

    def test_null_attribute_removed_by_a_later_catalog_is_a_change(self):
        operation = {
            "id": "probe.op", "version": 1, "requirement": "required", "surfaces": ["rust"],
            "input": {}, "output": {}, "side_effect": "none", "controls": {},
            "attributes": {"contract": "probe", "limit": None},
        }
        later = copy.deepcopy(operation)
        del later["attributes"]["limit"]
        versions = {"plenora-probe-tools": {1: {"operations": [operation]}, 2: {"operations": [later]}}}
        errors = validator.repeated_identity_errors(versions)
        self.assertTrue(any("changes attribute limit" in error for error in errors), errors)
        later["attributes"] = None
        errors = validator.repeated_identity_errors(versions)
        self.assertTrue(any("attributes are not an object" in error for error in errors), errors)


class NullCrashTests(unittest.TestCase):
    """A null where an object is expected is a validation error, never an
    exception that stops the gate."""

    @classmethod
    def setUpClass(cls):
        cls.catalogs = validator.load_catalogs()
        cls.schemas = {
            name: validator.load_json(ROOT / "schemas" / name) for name in validator.EXPECTED_SCHEMAS
        }
        cls.registry = validator.schema_registry(cls.schemas)

    def test_data_catalog_attributes_null(self):
        for version in (1, 2):
            with self.subTest(version=version):
                catalog = copy.deepcopy(validator.load_catalog_versions()[validator.DATA_COMPONENT][version])
                operation = next(
                    item for item in catalog["operations"] if (item["id"], item["version"]) == ("data.catalog", version)
                )
                operation["attributes"] = None
                self.assertTrue(validator.data_catalog_errors(catalog, version))
                operation["attributes"] = {"registry": 5}
                self.assertTrue(validator.data_catalog_errors(catalog, version))

    def test_data_run_attributes_null(self):
        for identity in [("data.run", 2), ("data.validate", 2), ("data.run", 3)]:
            with self.subTest(operation=identity):
                catalog = copy.deepcopy(self.catalogs[validator.DATA_COMPONENT])
                operation = next(
                    item for item in catalog["operations"] if (item["id"], item["version"]) == identity
                )
                operation["attributes"] = None
                self.assertTrue(validator.data_catalog_errors(catalog, 2))
        catalog = copy.deepcopy(validator.load_catalog_versions()[validator.DATA_COMPONENT][1])
        next(item for item in catalog["operations"] if item["id"] == "data.run")["attributes"] = None
        self.assertTrue(validator.data_catalog_errors(catalog, 1))

    def test_rest_request_input_and_connection_null(self):
        request = validator.load_json(ROOT / "examples/valid/rest-runtime-artifact-request.json")
        catalog = self.catalogs[validator.REST_COMPONENT]
        for name, change, reason in [
            ("input", lambda doc: doc.update(input=None), "input must be an object"),
            ("connection", lambda doc: doc["input"].update(connection=None), "connection must be an object"),
            ("method", lambda doc: doc["input"]["connection"].update(method=None), "method must be a string"),
        ]:
            with self.subTest(member=name):
                document = copy.deepcopy(request)
                change(document)
                errors = validator.rest_boundary_errors(document, catalog)
                self.assertTrue(any(reason in error for error in errors), errors)

    def test_storage_retry_and_payload_null(self):
        operation = next(
            item for item in self.catalogs[validator.STORAGE_COMPONENT]["operations"] if item["id"] == "storage.put"
        )
        for effect in ("unknown", "partial"):
            with self.subTest(remote_effect=effect):
                document = vector("storage-put-unknown-error.json")
                document["payload"].update(remote_effect=effect, retry=None)
                self.assertTrue(validator.storage_vector_errors(document, operation))
        document = vector("storage-put-unknown-error.json")
        document["payload"] = None
        self.assertEqual(
            validator.storage_vector_errors(document, operation), ["storage vector payload must be an object"]
        )

    def test_data_run_3_error_retry_null(self):
        for effect in ("unknown", "partial"):
            with self.subTest(remote_effect=effect):
                document = vector("data-run-partial-error-v3.json")
                document["payload"].update(remote_effect=effect, retry=None)
                errors = validator.data_run_3_vector_errors(document, self.schemas, self.registry)
                self.assertTrue(any("forbid automatic retry" in error for error in errors), errors)

    def test_data_run_3_manifest_with_nulls(self):
        request = vector("data-run-request-v3.json")
        for name, change in [
            ("artifact", lambda doc: doc["payload"]["outputs"][0].update(artifact=None)),
            ("output entry", lambda doc: doc["payload"]["outputs"].__setitem__(0, None)),
            ("steps", lambda doc: doc["payload"].update(steps=None)),
            ("payload", lambda doc: doc.update(payload=None)),
        ]:
            with self.subTest(member=name):
                success = vector("data-run-success-v3.json")
                change(success)
                self.assertTrue(validator.data_run_3_manifest_errors([request, success]))
        broken = vector("data-run-request-v3.json")
        broken["payload"]["plan"] = None
        self.assertTrue(validator.data_run_3_manifest_errors([broken, vector("data-run-success-v3.json")]))

    def test_data_run_3_error_location_with_null_plan(self):
        request = vector("data-run-request-v3.json")
        request["payload"]["plan"] = None
        error = vector("data-run-partial-error-v3.json")
        self.assertIsInstance(validator.data_run_3_error_location_errors([request, error]), list)
        request["payload"] = {"plan": {"inputs": None, "outputs": [None], "steps": [None, {"out": 3}]}}
        self.assertIsInstance(validator.data_run_3_error_location_errors([request, error]), list)
        error["payload"] = None
        self.assertIn(
            "a data.run 3 error payload is not an object",
            validator.data_run_3_error_location_errors([request, error]),
        )

    def test_runtime_error_vector_with_null_retry_or_payload(self):
        original = validator.load_json
        for name, change in [
            ("retry", lambda doc: doc["payload"].update(retry=None)),
            ("payload", lambda doc: doc.update(payload=None)),
        ]:
            def corrupted(path, change=change):
                document = original(path)
                if path.name == "data-run-timeout-error.json":
                    change(document)
                return document
            with self.subTest(member=name), patch.object(validator, "load_json", corrupted):
                failures = validator.validate_runtime_vectors(self.catalogs, self.schemas, self.registry)
                self.assertTrue(any("data-run-timeout-error.json" in failure for failure in failures), failures)


class SilentOverwriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = validator.load_catalogs()

    def test_two_requests_cannot_share_a_correlation(self):
        request = vector("data-run-request-v3.json")
        other = copy.deepcopy(request)
        other["metadata"]["plenora.message.id"] = "018f3d84-7b2c-7f00-8000-0000000001ff"
        other["payload"]["plan"]["outputs"] = []
        success = vector("data-run-success-v3.json")
        for check in (validator.data_run_3_manifest_errors, validator.data_run_3_error_location_errors):
            with self.subTest(check=check.__name__):
                errors = check([request, other, success])
                self.assertIn("two data.run 3 requests share one correlation id", errors)
                self.assertEqual(check([request, success]), [])

    def test_storage_coverage_names_the_version(self):
        catalogs = copy.deepcopy(self.catalogs)
        storage = catalogs[validator.STORAGE_COMPONENT]
        get = copy.deepcopy(next(item for item in storage["operations"] if item["id"] == "storage.get"))
        get["version"] = 2
        for direction in ("input", "output"):
            get[direction]["contract"] = get[direction]["contract"].replace("-v1", "-v2")
        storage["operations"].append(get)
        original = validator.load_json

        def moved(path):
            document = original(path)
            if path.name == "storage-get-success.json":
                document["metadata"]["plenora.operation.version"] = "2"
                document["metadata"]["plenora.output.contract"] = get["output"]["contract"]
            return document

        schemas = {name: original(ROOT / "schemas" / name) for name in validator.EXPECTED_SCHEMAS}
        with patch.object(validator, "load_json", moved):
            failures = validator.validate_runtime_vectors(catalogs, schemas, validator.schema_registry(schemas))
        self.assertTrue(
            any("coverage is incomplete" in failure and "'storage.get', 1, 'success'" in failure for failure in failures),
            failures,
        )

    def test_repeated_binding_section_is_rejected(self):
        original = validator.load_json

        def repeated(path):
            document = original(path)
            if path.name == "cli-v1.json":
                document["components"].append(copy.deepcopy(document["components"][0]))
            return document

        with patch.object(validator, "load_json", repeated):
            failures = validator.validate_bindings(self.catalogs)
        self.assertTrue(any("cli-v1.json must contain all five components exactly once" in f for f in failures), failures)

    def test_repeated_rest_capability_identity_is_rejected(self):
        document = validator.load_json(ROOT / "examples/valid/capabilities-rest-v2.json")
        document["operations"].append(copy.deepcopy(document["operations"][0]))
        errors = validator.rest_capability_errors(document, self.catalogs[validator.REST_COMPONENT])
        self.assertTrue(any("repeats an operation identity" in error for error in errors), errors)


class InternalErrorTests(unittest.TestCase):
    def test_unexpected_exception_is_reported_as_a_validator_defect(self):
        def broken(catalogs):
            raise KeyError("probe")

        with patch.object(validator, "validate_composition", broken),                 contextlib.redirect_stderr(io.StringIO()) as errors, contextlib.redirect_stdout(io.StringIO()):
            status = validator.main()
        self.assertEqual(status, 1)
        self.assertIn("internal validator error (KeyError", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_semantic_checks_do_not_run_on_a_structural_failure(self):
        original = validator.load_json

        def null_metadata(path):
            document = original(path)
            if path.name == "storage-put-request.json":
                document["metadata"] = None
            return document

        with patch.object(validator, "load_json", null_metadata),                 contextlib.redirect_stderr(io.StringIO()) as errors, contextlib.redirect_stdout(io.StringIO()):
            status = validator.main()
        self.assertEqual(status, 1)
        self.assertIn("storage-put-request.json must validate", errors.getvalue())
        self.assertNotIn("internal validator error", errors.getvalue())


class StrictJsonTests(unittest.TestCase):
    def test_repeated_key_is_rejected_at_every_depth(self):
        for text in ('{"a": 1, "a": 2}', '{"a": {"b": 1, "b": 1}}', '[{"x": null, "x": null}]'):
            with self.subTest(text=text):
                with self.assertRaises(validator.RepeatedKey):
                    validator.loads_json(text)
        self.assertEqual(validator.loads_json('{"a": {"a": 1}}'), {"a": {"a": 1}})

    def copy_repository(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for entry in ROOT.iterdir():
            if entry.name in {".git", "__pycache__"}:
                continue
            if entry.is_dir():
                shutil.copytree(entry, root / entry.name, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(entry, root / entry.name)
        return root

    def run_gate(self, root):
        with patch.object(validator, "ROOT", root), patch.object(validator, "SCHEMA_DIR", root / "schemas"), \
                contextlib.redirect_stderr(io.StringIO()) as errors, contextlib.redirect_stdout(io.StringIO()):
            status = validator.main()
        return status, errors.getvalue()

    def test_complete_gate_rejects_a_repeated_key(self):
        root = self.copy_repository()
        self.assertEqual(self.run_gate(root)[0], 0)
        path = root / "vectors/runtime-v1/storage-put-unknown-error.json"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace('"remote_effect": "unknown",', '"remote_effect": "none", "remote_effect": "unknown",', 1),
            encoding="utf-8",
        )
        status, output = self.run_gate(root)
        self.assertEqual(status, 1)
        self.assertIn("repeats a member name", output)

    def test_registry_file_outside_the_grammar_fails(self):
        root = self.copy_repository()
        shutil.copy2(root / "catalogs/data-kernels-v1.json", root / "catalogs/data-kernels-v01.json")
        status, output = self.run_gate(root)
        self.assertEqual(status, 1)
        self.assertIn("data-kernels-v01.json", output)


if __name__ == "__main__":
    unittest.main()
