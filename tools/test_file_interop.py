"""File descriptors, byte integrity, surface isolation and safe diagnostics."""

import copy
import unittest

import file_interop
import validate_specs as validator


class FileInteropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {
            path.name: validator.load_json(path)
            for path in validator.SCHEMA_DIR.glob("*.schema.json")
        }
        cls.registry = validator.schema_registry(cls.schemas)
        cls.matrix = validator.load_json(
            validator.ROOT / "composition/file-pipelines-v1.json")
        cls.vectors = [
            validator.load_json(path)
            for path in sorted((validator.ROOT / "vectors/file-interop-v1").glob("*.json"))
        ]

    def errors(self, document):
        return validator.instance_errors(
            self.schemas["file-interop-vector-v1.schema.json"],
            document, self.registry)

    def test_normative_vectors_and_coverage(self):
        self.assertEqual(len(self.matrix["edges"]), 4)
        for edge in self.matrix["edges"]:
            vectors = [v for v in self.vectors if v["edge"] == edge]
            self.assertEqual(
                {v["expect"].get("cause", "accepted") for v in vectors},
                {"accepted", "digest_mismatch", "content_type_mismatch",
                 "truncated_payload", "undeclared_format_family"})
        for vector in self.vectors:
            self.assertEqual(self.errors(vector), [])
            self.assertEqual(file_interop.vector_errors(vector, self.matrix["edges"]), [])
        self.assertEqual(validator.validate_file_interop(validator.load_catalogs()), [])

    def positive(self, surface="runtime"):
        return copy.deepcopy(next(
            v for v in self.vectors
            if v["expect"]["outcome"] == "accepted" and v["edge"]["surface"] == surface))

    def test_runtime_rejects_paths_and_extra_payload(self):
        for token in ("/private/data", "C:\\private\\data", "file:///tmp/a",
                      "\\\\server\\share", "artifact:../secret"):
            v = self.positive()
            v["file"]["reference"]["token"] = token
            self.assertTrue(self.errors(v))
        for key, value in (("path", "/private"), ("bytes", "secret"), ("authorized", True)):
            v = self.positive()
            v["file"]["reference"][key] = value
            self.assertTrue(self.errors(v))

    def test_invalid_descriptor_types_and_missing_fields(self):
        for key in self.positive()["file"]:
            v = self.positive()
            del v["file"][key]
            self.assertTrue(self.errors(v))
        for key, value in (("size_bytes", -1), ("size_bytes", True),
                           ("size_bytes", 1.5), ("sha256", "ABC"),
                           ("format_family", ""), ("content_type", "text")):
            v = self.positive()
            v["file"][key] = value
            self.assertTrue(self.errors(v))

    def test_version_surface_and_edge_are_checked(self):
        for change in (
            lambda v: v["file"]["producer"].update(version=99),
            lambda v: v["file"]["reference"].update(surface="cli"),
            lambda v: v["edge"]["to"]["operation"].update(version=99),
            lambda v: v["file"].update(format_family="arrow_ipc_file"),
        ):
            v = self.positive()
            change(v)
            self.assertTrue(file_interop.vector_errors(v, self.matrix["edges"]))

    def test_forged_expectation_and_excess_bytes(self):
        v = self.positive()
        v["resolved"]["bytes_hex"] += "00"
        self.assertEqual(file_interop.evaluate(v)["cause"], "size_mismatch")
        self.assertTrue(file_interop.vector_errors(v, self.matrix["edges"]))

    def test_errors_never_quote_values(self):
        v = self.positive()
        sentinel = "SENSITIVE_DOCUMENT_VALUE"
        v["resolved"]["content_type"] = sentinel
        result = file_interop.evaluate(v)
        self.assertNotIn(sentinel, str(result))
        self.assertEqual(result["message"], "File handoff rejected.")
        v["expect"]["message"] = sentinel
        self.assertNotIn(sentinel, str(self.errors(v)))

    def test_catalog_envelope_and_operation_validation(self):
        operations = validator.operation_index(validator.load_catalogs())
        for key, value in (("envelope_contract", "unknown"),):
            matrix = copy.deepcopy(self.matrix)
            matrix["edges"][0]["from"][key] = value
            self.assertTrue(file_interop.composition_errors(matrix, operations))
        matrix = copy.deepcopy(self.matrix)
        matrix["edges"][0]["from"]["operation"]["version"] = 99
        self.assertTrue(file_interop.composition_errors(matrix, operations))


if __name__ == "__main__":
    unittest.main()
