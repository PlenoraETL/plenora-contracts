"""Regression probe: a runtime vector exercises only an operation version
whose catalog selects the runtime surface, for every component."""

import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import validate_specs as validator


class RuntimeVectorSurfaceTests(unittest.TestCase):
    def test_gate_passes_unchanged(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(validator.main(), 0)

    def test_vector_for_an_operation_off_the_runtime_is_rejected(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("vectors/runtime-v1/database-query-success.json"):
                document = copy.deepcopy(document)
                metadata = document["metadata"]
                metadata["plenora.capability.operation"] = "database.transaction.commit"
                metadata["plenora.output.contract"] = "plenora-database-transaction-outcome-v1"
            return document

        stderr = io.StringIO()
        with patch.object(validator, "load_json", loader), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            self.assertNotEqual(validator.main(), 0)
        self.assertIn("does not select", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
