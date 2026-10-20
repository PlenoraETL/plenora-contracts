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
    def test_a_reused_id_does_not_return_another_registry_key(self):
        documents = schemas()
        before = validator.schema_registry(documents)
        after = validator.schema_registry(dict(documents, **{ERROR: stricter_error(documents[ERROR])}))
        gate = gate_fuzz.Gate()
        before_key = gate._registry_key(before)
        # Simulate an id collision without relying on allocator behavior.
        gate.registries[id(after)] = gate.registries[id(before)]
        after_key = gate._registry_key(after)
        self.assertNotEqual(before_key, after_key)
        self.assertEqual(after_key, gate_fuzz.Gate()._registry_key(after))
        self.assertIs(gate.registries[id(after)][0], after)
        self.assertEqual(gate._registry_key(before), before_key)

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
    def test_only_baseline_registries_survive_many_runs(self):
        path = (ROOT / "schemas" / ERROR).resolve()
        document = validator.load_json(path)
        with gate_fuzz.Gate() as gate:
            baseline = gate.registries.copy()
            self.assertEqual(len(baseline), 1)
            for index in range(100):
                mutated = copy.deepcopy(document)
                mutated["required"] = list(mutated["required"]) + [f"missing_{index}"]
                content = (json.dumps(mutated) + "\n").encode("utf-8")
                result = gate.run((path, content))
                self.assertNotEqual(result[0], 0)
                self.assertEqual(gate.registries, baseline)
                if index % 25 == 0:
                    self.assertEqual(result, gate.run_complete((path, content)))
                    self.assertEqual(gate.registries, baseline)

    def test_failed_runs_also_release_registries(self):
        with gate_fuzz.Gate() as gate:
            baseline = gate.registries.copy()

            def fail():
                gate._registry_key(validator.schema_registry({}))
                self.assertGreater(len(gate.registries), len(baseline))
                raise ValueError("failed mutation")

            with patch.object(validator, "main", fail):
                self.assertEqual(gate.run(None)[0], "ValueError")
            self.assertEqual(gate.registries, baseline)
            self.assertIsNone(gate.target)

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


    def test_a_constant_of_another_json_type_is_another_argument(self):
        """`1 == True` in Python, also inside a dictionary: a schema whose
        `const` 1 becomes `true` is another schema, and the validators that
        receive it run again instead of returning the unmutated result."""
        path = (ROOT / "schemas" / "arrow-metadata-vector-v1.schema.json").resolve()
        text = path.read_text(encoding="utf-8")
        self.assertIn('"schema_version": {"const": 1}', text)
        content = text.replace('"schema_version": {"const": 1}', '"schema_version": {"const": true}', 1).encode("utf-8")
        with gate_fuzz.Gate() as gate:
            memoized = gate.run((path, content))
            complete = gate.run_complete((path, content))
        self.assertNotEqual(complete[0], 0)
        self.assertEqual(memoized, complete)


class SameTests(unittest.TestCase):
    """`_same` compares arguments as JSON data: by type, then by value."""

    def test_json_types_are_distinct(self):
        pairs = (
            (1, True), (0, False), (1, 1.0), (0, 0.0), (True, 1.0),
            ({"a": 1}, {"a": True}), ([1], [1.0]), ((1,), (True,)),
            ({"a": [{"b": 0}]}, {"a": [{"b": False}]}), ({1}, {True}),
            ({"a": 1, "b": 2}, {"b": 2, "a": 1}), ("1", 1), (None, False),
        )
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                self.assertFalse(gate_fuzz._same(left, right))
                self.assertFalse(gate_fuzz._same(right, left))

    def test_equal_data_is_the_same(self):
        values = (1, True, 1.5, "x", None, {"a": [1, {"b": True}]}, (1, "a"), {1, 2}, frozenset({"x"}),
                  float("nan"))
        for value in values:
            with self.subTest(value=value):
                self.assertTrue(gate_fuzz._same(value, copy.deepcopy(value)))

    def test_deep_arguments_compare_without_recursion(self):
        def nested(leaf):
            value = leaf
            for _ in range(10_000):
                value = {"a": [value]}
            return value

        self.assertTrue(gate_fuzz._same(nested(1), nested(1)))
        self.assertFalse(gate_fuzz._same(nested(1), nested(True)))

    def test_registries_compare_by_their_schemas(self):
        documents = schemas()
        before = validator.schema_registry(documents)
        self.assertTrue(gate_fuzz._same(before, validator.schema_registry(copy.deepcopy(documents))))
        mutated = copy.deepcopy(documents)
        mutated[ERROR]["required"] = list(mutated[ERROR]["required"]) + ["zzz_required"]
        self.assertFalse(gate_fuzz._same(before, validator.schema_registry(mutated)))

    def test_an_object_of_another_kind_is_the_same_only_as_itself(self):
        marker = object()
        self.assertTrue(gate_fuzz._same(marker, marker))
        self.assertFalse(gate_fuzz._same(object(), object()))
        self.assertFalse(gate_fuzz._same([marker], [object()]))


if __name__ == "__main__":
    unittest.main()
