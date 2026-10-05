"""Regression probes for the private-path and inline-credential guards of
REST and storage runtime requests. The guards are fixture heuristics with a
declared limit (`LOCAL_PATH` in validate_specs.py); these probes pin the
spellings they must recognize and the positive rule for artifact references.
"""

import copy
import unittest

import validate_specs as validator

ROOT = validator.ROOT


class LocalPathTests(unittest.TestCase):
    def test_local_spellings_are_recognized(self):
        for value in [
            "/etc/passwd", "\\\\server\\share\\x", "C:\\data\\x", "C:/data/x",
            "C:relative\\x", "c:x", "./x", ".\\x", ".", "..", "../x", "a/../b", "a\\..\\b",
            "artifact://x/./y", "~/x", "~user/x", "~\\x", "%TEMP%\\x", "%userprofile%/x",
            "$HOME/x", "${HOME}/x", "x/$TMPDIR/y", "file:///x", "FILE:x", "artifact://x/%2E%2e/y",
        ]:
            with self.subTest(value=value):
                self.assertTrue(validator.is_local_path(value))

    def test_opaque_references_are_not_local(self):
        for value in [
            "artifact://tenant-a/8d936f1d", "secret://rest/production", "s3://bucket/key.csv",
            "artifact://x/100%25", "artifact://x/a$b", "artifact://x/v1.2/y",
        ]:
            with self.subTest(value=value):
                self.assertFalse(validator.is_local_path(value))
                self.assertTrue(validator.is_opaque_reference(value))

    def test_only_opaque_references_are_artifact_references(self):
        for value in [
            "report.csv", "exports/report.csv", "C:x", "a:b", "file:///x", "artifact://x/../y",
            "artifact://x y", "artifact:\\\\x", "", None, 5, "x" * 2049,
        ]:
            with self.subTest(value=value):
                self.assertFalse(validator.is_opaque_reference(value))


class RestBoundaryHeuristicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validator.load_catalogs()[validator.REST_COMPONENT]
        cls.request = validator.load_json(ROOT / "examples/valid/rest-runtime-artifact-request.json")

    def errors(self, change):
        document = copy.deepcopy(self.request)
        change(document["input"])
        return validator.rest_boundary_errors(document, self.catalog)

    def test_valid_request_conforms(self):
        self.assertEqual(validator.rest_boundary_errors(self.request, self.catalog), [])

    def test_reference_without_a_path_marker_is_still_rejected(self):
        for reference in ["report.csv", "exports/report.csv", "./report.csv", "~/report.csv", "%TEMP%\\r.csv"]:
            with self.subTest(reference=reference):
                errors = self.errors(lambda payload: payload["artifact_source"].update(reference=reference))
                self.assertTrue(any("opaque artifact reference" in error for error in errors), errors)

    def test_missing_reference_is_rejected(self):
        errors = self.errors(lambda payload: payload["artifact_source"].pop("reference"))
        self.assertTrue(any("opaque artifact reference" in error for error in errors), errors)

    def test_credential_member_names_are_normalized(self):
        for key in [
            "apiKey", "X-Api-Key", "client_secret", "clientSecret", "access_token", "refresh-token",
            "Authorization", "proxy_authorization", "password_hash", "privateKey", "session.cookie",
            "credentials", "secret_ref",
        ]:
            with self.subTest(key=key):
                errors = self.errors(lambda payload: payload["connection"].update({key: "x"}))
                self.assertTrue(any("inline credential field" in error for error in errors), errors)

    def test_credential_values_are_recognized_under_any_name(self):
        for value in ["Bearer abc.def", "basic dXNlcjpwYXNz", "-----BEGIN RSA PRIVATE KEY-----\nMII"]:
            with self.subTest(value=value):
                errors = self.errors(lambda payload: payload["connection"].update(headers=[{"value": value}]))
                self.assertTrue(any("inline credential value" in error for error in errors), errors)

    def test_secret_reference_must_be_opaque(self):
        errors = self.errors(lambda payload: payload["connection"].update(credential_ref="hunter2"))
        self.assertTrue(any("credential_ref" in error for error in errors), errors)
        errors = self.errors(lambda payload: payload["connection"].update(secret_reference="vault://kv/rest"))
        self.assertEqual(errors, [])


class StorageHeuristicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operations = {
            (item["id"], item["version"]): item
            for item in validator.load_catalogs()[validator.STORAGE_COMPONENT]["operations"]
        }

    def errors(self, change):
        vector = validator.load_json(ROOT / "vectors/runtime-v1/storage-put-request.json")
        change(vector["payload"])
        return validator.storage_vector_errors(vector, self.operations[("storage.put", 1)])

    def test_unchanged_request_conforms(self):
        self.assertEqual(self.errors(lambda payload: None), [])

    def test_credential_member_names_are_normalized(self):
        for key in ["apiKey", "client_secret", "access_token", "SecretAccessKey", "sas-token"]:
            with self.subTest(key=key):
                errors = self.errors(lambda payload: payload["connection"].update({key: "x"}))
                self.assertTrue(any("inline credential field" in error for error in errors), errors)

    def test_local_paths_anywhere_in_the_payload(self):
        for value in ["./x", "~/x", "C:relative\\x", "%TEMP%\\x", "$HOME/x"]:
            with self.subTest(value=value):
                errors = self.errors(lambda payload: payload.update(note=value))
                self.assertTrue(any("private local path" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
