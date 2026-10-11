"""The harness of the fuzzers (decision 0021) is itself checked: its caches
never return a verdict computed under other inputs, and the oracle of the
memoized path runs without them."""

from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import gate_fuzz
import validate_specs as validator
from gate_fuzz import ROOT

ENVELOPE = "cli-envelope-v2.schema.json"
ERROR = "error-v1.schema.json"


def schemas() -> dict:
    return {name: validator.load_json(ROOT / "schemas" / name) for name in validator.EXPECTED_SCHEMAS}


def stricter_error(schema: dict) -> dict:
    """error-v1 with one more required member: an envelope that carries an
    error, valid before, is invalid under it through its `$ref`."""
    mutated = copy.deepcopy(schema)
    mutated["required"] = list(mutated["required"]) + ["zzz_required"]
    return mutated


class VerdictCacheTests(unittest.TestCase):
    def test_the_key_includes_the_referenced_schemas(self):
        """Same schema, same instance, another registry: the `$ref` of the
        envelope resolves to another error schema, so the verdict differs."""
        documents = schemas()
        instance = validator.load_json(ROOT / "examples/valid/cli-error.json")
        before = validator.schema_registry(documents)
        after = validator.schema_registry(dict(documents, **{ERROR: stricter_error(documents[ERROR])}))
        self.assertEqual(validator.instance_errors(documents[ENVELOPE], instance, before), [])
        self.assertNotEqual(validator.instance_errors(documents[ENVELOPE], instance, after), [])
        for shared in (False, True):
            with self.subTest(shared=shared):
                gate = gate_fuzz.Gate()
                gate._real_instance_errors = validator.instance_errors
                gate.shared = {id(documents[ENVELOPE]), id(instance)} if shared else set()
                self.assertEqual(gate._instance_errors(documents[ENVELOPE], instance, before), [])
                self.assertNotEqual(gate._instance_errors(documents[ENVELOPE], instance, after), [])
                self.assertEqual(gate._instance_errors(documents[ENVELOPE], instance, before), [])

    def test_the_complete_run_uses_no_cache(self):
        """`run_complete`, the oracle of the memoized path, computes every
        verdict, parse and schema check again."""
        gate = gate_fuzz.Gate()
        gate.memo = False
        calls = {"verdicts": 0, "loads": 0, "checks": 0}

        def counted(name, function):
            def wrapper(*args, **kwargs):
                calls[name] += 1
                return function(*args, **kwargs)
            return wrapper

        gate._real_instance_errors = counted("verdicts", lambda *args: [])
        gate._real_loads = counted("loads", json.loads)
        gate._real_check_schema = counted("checks", lambda *args, **kwargs: None)
        schema, instance, registry = {"type": "object"}, {}, object()
        gate.shared = {id(schema), id(instance)}
        gate.verdicts[(id(schema), id(instance))] = ["stale"]
        gate.checked.add(id(schema))
        text = '{"a": 1}'
        gate.parsed[text] = {"stale": True}
        for _ in range(2):
            self.assertEqual(gate._instance_errors(schema, instance, registry), [])
            self.assertEqual(gate._loads(text), {"a": 1})
            gate._check_schema(schema)
        self.assertEqual(calls, {"verdicts": 2, "loads": 2, "checks": 2})


class EndToEndTests(unittest.TestCase):
    def test_a_mutated_referenced_schema_reaches_the_envelope(self):
        """In the harness, mutating error-v1 makes the CLI error envelope
        fail through its `$ref`, in the memoized run and in the oracle."""
        path = (ROOT / "schemas" / ERROR).resolve()
        content = (json.dumps(stricter_error(validator.load_json(path)), indent=2) + "\n").encode("utf-8")
        with gate_fuzz.Gate() as gate:
            memoized = gate.run((path, content))
            complete = gate.run_complete((path, content))
        self.assertEqual(memoized, complete)
        self.assertIn("examples/valid/cli-error.json must validate", memoized[1])


if __name__ == "__main__":
    unittest.main()
