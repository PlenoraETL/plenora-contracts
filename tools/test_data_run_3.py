"""Regression probes for `data.run` 3, the runtime representation of a data
plan with named outputs (profile data-tools v2, DT-RUN-001..DT-RUN-008).

Each probe breaks one document in memory and expects the gate to notice.
"""

import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import validate_specs as validator

VECTORS = validator.ROOT / "vectors/runtime-v1"


class DataRun3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validator.load_catalogs()[validator.DATA_COMPONENT]
        cls.schemas = {
            name: validator.load_json(validator.ROOT / "schemas" / name)
            for name in validator.EXPECTED_SCHEMAS
        }
        cls.registry = validator.schema_registry(cls.schemas)
        cls.request = validator.load_json(VECTORS / "data-run-request-v3.json")
        cls.success = validator.load_json(VECTORS / "data-run-success-v3.json")
        cls.error = validator.load_json(VECTORS / "data-run-partial-error-v3.json")

    def run3(self, catalog):
        return next(
            item for item in catalog["operations"]
            if item["id"] == "data.run" and item["version"] == 3
        )

    def vector_errors(self, vector):
        return validator.data_run_3_vector_errors(vector, self.schemas, self.registry)

    def test_unchanged_documents_conform(self):
        self.assertEqual(validator.data_catalog_errors(self.catalog, 2), [])
        for vector in (self.request, self.success, self.error):
            self.assertEqual(self.vector_errors(vector), [])

    def test_catalog_entry_is_pinned(self):
        cases = {
            "local side effect": lambda op: op.update(side_effect="local"),
            "on the CLI": lambda op: op["surfaces"].append("cli"),
            "required": lambda op: op.update(requirement="required"),
            "arrow payload": lambda op: op["output"]["content_types"].append(
                "application/vnd.apache.arrow.stream"
            ),
            "another registry": lambda op: op["attributes"].update(
                kernel_registry="plenora-data-kernel-catalog-v1"
            ),
            "parquet as interchange": lambda op: op["attributes"]["artifact_content_types"][
                "sink"
            ].append("application/vnd.apache.parquet"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                catalog = copy.deepcopy(self.catalog)
                mutate(self.run3(catalog))
                self.assertTrue(validator.data_catalog_errors(catalog, 2))
        missing = copy.deepcopy(self.catalog)
        missing["operations"].remove(self.run3(missing))
        self.assertTrue(validator.data_catalog_errors(missing, 2))

    def test_request_is_checked(self):
        cases = {
            "missing source": lambda p: p["inputs"].clear(),
            "extra source": lambda p: p["inputs"].update(
                other={"reference": "artifact://input/x", "content_type": "application/vnd.apache.arrow.file"}
            ),
            "extra sink": lambda p: p["outputs"].update(
                other={"reference": "artifact://output/x", "content_type": "application/vnd.apache.arrow.file", "overwrite": False}
            ),
            "file reference": lambda p: p["inputs"]["parcels"].update(reference="file:///tmp/parcels.parquet"),
            "dot-dot reference": lambda p: p["inputs"]["parcels"].update(reference="artifact://input/../secret"),
            "drive path": lambda p: p["inputs"]["parcels"].update(reference="C:\\data\\parcels.parquet"),
            "sink without overwrite": lambda p: p["outputs"]["large"].pop("overwrite"),
            "unknown content type": lambda p: p["outputs"]["large"].update(content_type="text/csv"),
            "bad digest": lambda p: p["inputs"]["parcels"]["expected"].update(sha256="ABC"),
            "empty expectation": lambda p: p["inputs"]["parcels"].update(expected={}),
            "unknown field": lambda p: p.update(path="/tmp"),
            "invalid plan": lambda p: p["plan"].update(outputs=["nowhere"]),
            "unknown kernel": lambda p: p["plan"]["steps"][0].update(op="table.filter_rows"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                vector = copy.deepcopy(self.request)
                mutate(vector["payload"])
                self.assertTrue(self.vector_errors(vector))

    def test_two_sinks_cannot_share_a_reference(self):
        vector = copy.deepcopy(self.request)
        payload = vector["payload"]
        payload["plan"]["outputs"].append("parcels_copy")
        payload["plan"]["steps"].append(
            {"out": "parcels_copy", "op": "table.select_columns", "in": ["parcels"], "config": {"columns": ["area"]}}
        )
        payload["outputs"]["parcels_copy"] = dict(payload["outputs"]["large"])
        errors = self.vector_errors(vector)
        self.assertTrue(any("share" in error for error in errors), errors)

    def test_result_is_checked(self):
        cases = {
            "repeated output": lambda p: p["outputs"].append(copy.deepcopy(p["outputs"][0])),
            "no digest": lambda p: p["outputs"][0]["artifact"].pop("sha256"),
            "negative size": lambda p: p["outputs"][0]["artifact"].update(size=-1),
            "local reference": lambda p: p["outputs"][0].update(reference="file:///tmp/large.arrow"),
            "no outputs": lambda p: p.update(outputs=[]),
            "path leaked": lambda p: p["outputs"][0].update(path="/tmp/large.arrow"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                vector = copy.deepcopy(self.success)
                mutate(vector["payload"])
                self.assertTrue(self.vector_errors(vector))

    def test_partial_and_unknown_publication_forbid_retry(self):
        for effect, retry in (("partial", "safe"), ("unknown", "never")):
            with self.subTest(effect=effect):
                vector = copy.deepcopy(self.error)
                vector["payload"]["remote_effect"] = effect
                vector["payload"]["retry"] = {"kind": retry}
                self.assertTrue(self.vector_errors(vector))

    def test_gate_requires_every_vector_kind(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("vectors/runtime-v1/data-run-success-v3.json"):
                document = copy.deepcopy(document)
                document["metadata"]["plenora.operation.version"] = "1"
                document["metadata"]["plenora.output.contract"] = "plenora-data-execution-result-v1"
                document["content_type"] = "application/vnd.apache.arrow.stream"
                document["payload"] = {}
            return document

        stderr = io.StringIO()
        with patch.object(validator, "load_json", loader), contextlib.redirect_stdout(
            io.StringIO()
        ), contextlib.redirect_stderr(stderr):
            self.assertNotEqual(validator.main(), 0)
        self.assertIn("data.run 3 runtime vector coverage", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
