"""Regression probes for storage targets and runtime boundary semantics.

Payload schemas and installed SDK qualification remain component-owned. These
tests mutate illustrative vectors to exercise the shared contract gate.
"""

import copy
import unittest
from unittest.mock import patch

import validate_specs as validator


class StorageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = validator.load_catalogs()
        cls.operations = {
            item["id"]: item
            for item in cls.catalogs[validator.STORAGE_COMPONENT]["operations"]
        }
        cls.schemas = {
            path.name: validator.load_json(path)
            for path in validator.SCHEMA_DIR.glob("*.schema.json")
        }
        cls.registry = validator.schema_registry(cls.schemas)

    def vector(self, name):
        return validator.load_json(validator.ROOT / "vectors/runtime-v1" / f"storage-{name}.json")

    def errors(self, vector):
        # Negative payloads still satisfy the shared envelope schema. Rejecting
        # them must exercise storage semantics, not an unrelated envelope guard.
        self.assertEqual(validator.instance_errors(
            self.schemas["runtime-vector-v1.schema.json"], vector, self.registry
        ), [])
        operation = self.operations[vector["metadata"]["plenora.capability.operation"]]
        return validator.storage_vector_errors(vector, operation)

    def assert_rejected(self, vector, reason):
        errors = self.errors(vector)
        self.assertTrue(any(reason in error for error in errors), errors)

    def test_selected_catalog_and_bindings_conform(self):
        self.assertEqual(validator.validate_catalog_semantics(self.catalogs), [])
        self.assertEqual(validator.validate_bindings(self.catalogs), [])

    def test_python_surface_cannot_disappear_from_one_operation(self):
        catalogs = copy.deepcopy(self.catalogs)
        catalogs[validator.STORAGE_COMPONENT]["operations"][0]["surfaces"].remove("python_sdk")
        self.assertTrue(validator.validate_catalog_semantics(catalogs))

    def test_each_sdk_operation_requires_sync_and_async_symbols(self):
        load = validator.load_json
        for operation in self.operations:
            for mode in ("Engine", "AsyncEngine"):
                with self.subTest(operation=operation, missing=mode):
                    document = load(validator.ROOT / "bindings/python-sdk-v1.json")
                    section = next(item for item in document["components"] if item["component"] == validator.STORAGE_COMPONENT)
                    binding = next(item for item in section["bindings"] if item["operation"] == operation)
                    binding["entrypoints"] = [item for item in binding["entrypoints"] if not item.startswith(mode + ".")]
                    with patch.object(validator, "load_json", side_effect=lambda path: document if path.name == "python-sdk-v1.json" else load(path)):
                        errors = validator.validate_bindings(self.catalogs)
                    self.assertTrue(any("both canonical SDK API modes" in error for error in errors), errors)

    def test_all_storage_vectors_conform(self):
        for path in (validator.ROOT / "vectors/runtime-v1").glob("storage-*.json"):
            with self.subTest(path=path.name):
                self.assertEqual(self.errors(validator.load_json(path)), [])
        self.assertEqual(validator.validate_runtime_vectors(self.catalogs, self.schemas, self.registry), [])

    def test_sdk_identity_and_discovery_cannot_be_substituted(self):
        load = validator.load_json
        for field, value, reason in (("artifact", "another-package", "distribution and import"),
                                     ("discovery", ["plenora_storage.version", "Engine.capabilities"], "discovery in both API modes")):
            with self.subTest(field=field):
                document = load(validator.ROOT / "bindings/python-sdk-v1.json")
                section = next(item for item in document["components"] if item["component"] == validator.STORAGE_COMPONENT)
                section[field] = value
                with patch.object(validator, "load_json", side_effect=lambda path: document if path.name == "python-sdk-v1.json" else load(path)):
                    errors = validator.validate_bindings(self.catalogs)
                self.assertTrue(any(reason in error for error in errors), errors)

    def test_missing_component_binding_reports_failure_without_crashing(self):
        load = validator.load_json
        for component in (validator.STORAGE_COMPONENT, validator.DATABASE_COMPONENT):
            with self.subTest(component=component):
                document = load(validator.ROOT / "bindings/python-sdk-v1.json")
                document["components"] = [item for item in document["components"] if item["component"] != component]
                with patch.object(validator, "load_json", side_effect=lambda path: document if path.name == "python-sdk-v1.json" else load(path)):
                    errors = validator.validate_bindings(self.catalogs)
                self.assertTrue(any("all five components" in error for error in errors), errors)

    def test_missing_operation_request_is_detected(self):
        load = validator.load_json
        replacement = self.vector("test-request")
        with patch.object(validator, "load_json", side_effect=lambda path: replacement if path.name == "storage-copy-request.json" else load(path)):
            errors = validator.validate_runtime_vectors(self.catalogs, self.schemas, self.registry)
        self.assertTrue(any("coverage is incomplete" in error and "storage.copy" in error for error in errors), errors)

    def test_policies_are_explicit_booleans_or_publication_modes(self):
        for action, field in (("get", "overwrite"), ("put", "overwrite"), ("copy", "overwrite"),
                              ("put", "publication_policy"), ("copy", "publication_policy"), ("delete", "ignore_missing")):
            for invalid in (None, "implicit", 1):
                with self.subTest(action=action, field=field, invalid=invalid):
                    vector = self.vector(f"{action}-request")
                    node = vector["payload"]["artifact_sink"] if action == "get" else vector["payload"]
                    if invalid is None:
                        node.pop(field)
                    else:
                        node[field] = invalid
                    self.assert_rejected(vector, "explicit")

    def test_source_and_sink_roles_cannot_be_interchanged(self):
        for action, required, forbidden in (("get", "artifact_sink", "artifact_source"), ("put", "artifact_source", "artifact_sink")):
            with self.subTest(action=action):
                vector = self.vector(f"{action}-request")
                vector["payload"][forbidden] = vector["payload"].pop(required)
                self.assert_rejected(vector, f"requires {required}")
                self.assert_rejected(vector, f"forbids {forbidden}")

    def test_artifact_references_are_nonempty_bounded_and_opaque(self):
        for action, role in (("get", "artifact_sink"), ("put", "artifact_source")):
            for value in ("artifact://", "artifact://" + "a" * 502, "artifact://has space", "artifact://x\n", "artifact://x/../secret", "/private/file", "C:\\private\\file", "file:///private/file"):
                with self.subTest(action=action, value=value):
                    vector = self.vector(f"{action}-request")
                    vector["payload"][role]["reference"] = value
                    self.assert_rejected(vector, "artifact reference")

    def test_inline_credentials_and_local_paths_are_rejected(self):
        for action in self.operations:
            for field, value, reason in (("password", "synthetic-canary", "inline credential"), ("path", "/private/file", "private local path")):
                with self.subTest(action=action, field=field):
                    vector = self.vector(f"{action.split('.')[1]}-request")
                    vector["payload"]["connection"]["config"][field] = value
                    self.assert_rejected(vector, reason)

    def test_artifact_metadata_is_bounded_and_typed(self):
        for action, role in (("get", "artifact_sink"), ("put", "artifact_source")):
            for field, value in (("size", True), ("size", -1), ("content_type", "text/" + "a" * 251), ("sha256", "etag-not-a-digest")):
                with self.subTest(action=action, field=field):
                    vector = self.vector(f"{action}-request")
                    vector["payload"][role]["metadata"][field] = value
                    self.assert_rejected(vector, "metadata")

    def test_unknown_request_metadata_does_not_invent_integrity(self):
        for action, role in (("get", "artifact_sink"), ("put", "artifact_source")):
            vector = self.vector(f"{action}-request")
            vector["payload"][role]["metadata"] = dict(content_type=None, size=None, sha256=None)
            self.assertEqual(self.errors(vector), [])

    def test_exact_metadata_and_reference_limits_remain_valid(self):
        for action, role in (("get", "artifact_sink"), ("put", "artifact_source")):
            vector = self.vector(f"{action}-request")
            vector["payload"][role]["reference"] = "artifact://" + "a" * 501
            vector["payload"][role]["metadata"].update(size=0, content_type="text/" + "a" * 250)
            self.assertEqual(self.errors(vector), [])
        for action in ("get", "put"):
            vector = self.vector(f"{action}-success")
            vector["payload"]["bytes_transferred"] = 0
            vector["payload"]["artifact"]["size"] = 0
            self.assertEqual(self.errors(vector), [])

    def test_transfer_integrity_and_byte_count_must_agree(self):
        for action in ("get", "put"):
            for field, value, reason in (("sha256", "f" * 64, "conflicts with checksum"), ("size", 18, "conflicts with byte count")):
                with self.subTest(action=action, field=field):
                    vector = self.vector(f"{action}-success")
                    vector["payload"]["artifact"][field] = value
                    self.assert_rejected(vector, reason)

    def test_transfer_byte_count_is_required_and_not_boolean(self):
        for action in ("get", "put"):
            for value in (None, True, -1):
                with self.subTest(action=action, value=value):
                    vector = self.vector(f"{action}-success")
                    vector["payload"]["artifact"]["size"] = 1 if value is True else value
                    if value is None:
                        vector["payload"].pop("bytes_transferred")
                    else:
                        vector["payload"]["bytes_transferred"] = value
                    self.assert_rejected(vector, "byte count")

    def test_cursor_validation_covers_request_and_result(self):
        for name, field in (("list-request", "cursor"), ("list-success", "next_cursor")):
            vector = self.vector(name)
            vector["payload"][field] = "cursor://" + "f" * 505
            self.assert_rejected(vector, "opaque and bounded")

    def test_partial_and_unknown_effects_forbid_automatic_retry(self):
        for name in ("get-partial-error", "put-unknown-error"):
            for retry in ({"kind": "safe"}, {"kind": "after", "delay_ms": 10}, {"kind": "requires_idempotency_key"}):
                with self.subTest(name=name, retry=retry):
                    vector = self.vector(name)
                    vector["payload"]["retry"] = retry
                    self.assert_rejected(vector, "recovery" if name.startswith("put") else "automatic retry")

    def test_complete_gate_rejects_partial_safe_retry(self):
        load = validator.load_json
        vector = self.vector("get-partial-error")
        vector["payload"]["retry"] = {"kind": "safe"}
        self.assertEqual(validator.instance_errors(self.schemas["error-v1.schema.json"], vector["payload"], self.registry), [])
        with patch.object(validator, "load_json", side_effect=lambda path: vector if path.name == "storage-get-partial-error.json" else load(path)):
            errors = validator.validate_runtime_vectors(self.catalogs, self.schemas, self.registry)
        self.assertTrue(any("automatic retry" in error for error in errors), errors)

    def test_partial_effect_retains_manual_recovery_options(self):
        for kind in ("never", "quarantine", "requires_recovery"):
            vector = self.vector("get-partial-error")
            vector["payload"]["retry"] = {"kind": kind}
            self.assertEqual(self.errors(vector), [])


if __name__ == "__main__":
    unittest.main()
