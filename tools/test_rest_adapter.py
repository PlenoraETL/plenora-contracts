"""REST-to-Arrow Adapter 1.0 (decision 0017): the reference adapter behind
the vectors, and the gate that compares each vector with it."""

import copy
import json
import unittest

import rest_adapter as adapter
import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/rest-arrow-adapter-v1"


def vector(name):
    return validator.load_json(VECTORS / name)


def declaration(*fields, **options):
    return {
        "schema_version": 1,
        "contract": "plenora-rest-arrow-adapter-v1",
        "accept_status": options.get("accept", ["success"]),
        "on_record_error": options.get("on_error", "fail"),
        "undeclared_members": options.get("undeclared", "ignore"),
        "fields": [
            {"name": name, "field_id": index, "pointer": pointer, "type": kind, "nullable": nullable}
            for index, (name, pointer, kind, nullable) in enumerate(fields)
        ],
    }


def result(*records, status="success"):
    return {"schema_version": 1, "status": status,
            "output": {"type": "records", "records": list(records)}, "errors": []}


class ConversionTests(unittest.TestCase):
    def test_types_without_coercion(self):
        cases = [
            ("bool", True, True), ("bool", 1, None),
            ("int64", -(2**63), -(2**63)), ("int64", 2**63, None), ("int64", 1.0, None),
            ("int64", False, None),
            ("float64", 2, 2.0), ("float64", float("inf"), None), ("float64", 10**400, None),
            ("float64", "1", None),
            ("utf8", "x", "x"), ("utf8", 1, None), ("utf8", [], None),
        ]
        for kind, value, expected in cases:
            with self.subTest(kind=kind, value=value):
                if expected is None:
                    with self.assertRaises(adapter.RecordError):
                        adapter.convert(value, kind, False)
                else:
                    self.assertEqual(adapter.convert(value, kind, False), expected)

    def test_null_and_missing(self):
        self.assertIsNone(adapter.convert(None, "utf8", True))
        self.assertIsNone(adapter.convert(adapter.MISSING, "int64", True))
        with self.assertRaises(adapter.RecordError) as raised:
            adapter.convert(adapter.MISSING, "int64", False)
        self.assertEqual(raised.exception.cause, "adapter.null_in_non_nullable")

    def test_pointer_evaluation(self):
        record = {"a": [{"b": 1}], "x~y": {"p/q": 2}}
        self.assertEqual(adapter.evaluate(record, "/a/0/b"), 1)
        self.assertEqual(adapter.evaluate(record, "/x~0y/p~1q"), 2)
        self.assertIs(adapter.evaluate(record, "/a/1"), adapter.MISSING)
        self.assertIs(adapter.evaluate(record, "/z"), adapter.MISSING)
        for pointer in ("/a/01", "/a/-", "/a/0/b/c"):
            with self.subTest(pointer), self.assertRaises(adapter.RecordError):
                adapter.evaluate(record, pointer)

    def test_declaration_errors(self):
        good = declaration(("a", "/a", "int64", True))
        self.assertEqual(adapter.declaration_errors(good), [])
        twice = declaration(("a", "/a", "int64", True), ("a", "/b", "int64", True))
        self.assertIn("repeated field name", adapter.declaration_errors(twice))
        for pointer in ("", "a", "/a~2", "/~"):
            bad = declaration(("a", pointer, "int64", True))
            with self.subTest(pointer):
                self.assertEqual(len(adapter.declaration_errors(bad)), 1)


class AdaptTests(unittest.TestCase):
    def test_error_outcomes_name_record_field_and_cause(self):
        outcome = adapter.adapt(declaration(("n", "/n", "int64", False)), result({"n": 1}, {"n": "2"}))
        self.assertEqual(outcome.as_expect(), {
            "outcome": "error", "category": "data_mapping", "record": 1, "field": "n",
            "cause": "adapter.type_mismatch",
        })

    def test_undeclared_members_are_checked_after_the_fields(self):
        decl = declaration(("n", "/n", "int64", False), undeclared="reject")
        outcome = adapter.adapt(decl, result({"n": "x", "extra": 1}))
        self.assertEqual(outcome.cause, "adapter.type_mismatch")
        outcome = adapter.adapt(decl, result({"n": 1, "extra": 1}))
        self.assertEqual((outcome.field, outcome.cause), ("extra", "adapter.undeclared_member"))

    def test_output_without_records(self):
        missing = {"schema_version": 1, "status": "success", "output": {"type": "records"}, "errors": []}
        self.assertEqual(adapter.adapt(declaration(("n", "/n", "int64", True)), missing).category, "schema")


class VectorTests(unittest.TestCase):
    def test_every_published_vector_agrees_with_the_reference(self):
        self.assertEqual(validator.validate_rest_adapter_vectors(), [])
        self.assertGreaterEqual(len(list(VECTORS.glob("*.json"))), 19)

    def test_a_wrong_outcome_is_reported(self):
        document = vector("records-in-order.json")
        document["expect"]["rows"].reverse()
        self.assertEqual(len(adapter.vector_errors(document)), 1)
        document = vector("error-partial-not-accepted.json")
        document["expect"]["category"] = "data_mapping"
        self.assertEqual(len(adapter.vector_errors(document)), 1)

    def test_an_integer_and_a_float_are_different_values(self):
        document = vector("records-in-order.json")
        document["expect"]["rows"][0]["id"] = 3.0
        self.assertEqual(len(adapter.vector_errors(document)), 1)
        document = vector("records-in-order.json")
        document["expect"]["rows"][1]["active"] = 0
        self.assertEqual(len(adapter.vector_errors(document)), 1)

    def test_a_float_field_may_be_written_as_an_integer(self):
        document = vector("records-in-order.json")
        self.assertEqual(document["expect"]["rows"][2]["score"], 2.0)
        document["expect"]["rows"][2]["score"] = 2
        self.assertEqual(adapter.vector_errors(document), [])

    def test_the_gate_reports_an_empty_directory(self):
        original = validator.ROOT
        try:
            validator.ROOT = original / "tools"
            self.assertEqual(
                validator.validate_rest_adapter_vectors(),
                ["vectors/rest-arrow-adapter-v1 has no vectors"],
            )
        finally:
            validator.ROOT = original

    def test_the_overflow_vector_keeps_its_literal(self):
        text = (VECTORS / "error-float-overflow.json").read_text(encoding="utf-8")
        self.assertIn("1e400", text)
        self.assertEqual(copy.deepcopy(json.loads(text))["expect"]["cause"], "adapter.not_representable")


if __name__ == "__main__":
    unittest.main()
