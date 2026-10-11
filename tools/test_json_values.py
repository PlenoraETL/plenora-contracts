"""JSON data compares by type and by value (`1`, `1.0` and `true` differ):
`json_values` and every check that compares two documents, or a document
with an expected value. Python's `==` takes `1`, `1.0` and `True` for the
same value, also inside a list or a dictionary."""

import copy
import json
import time
import unittest
from decimal import Decimal
from pathlib import Path

import check_schema_immutability as immutability
import messages
import validate_specs as validator
from conformance_checks import adoption_errors
from json_values import document_key, same_document, same_schema_value, schema_value_key

ROOT = Path(__file__).resolve().parents[1]
DIFFERENT = (
    (1, True), (0, False), (1, 1.0), (0, 0.0), (True, 1.0), (0.0, -0.0), (None, False), ("1", 1),
    ([1], [True]), ((1,), (1.0,)), ({"a": 1}, {"a": True}), ({"a": [{"b": 0}]}, {"a": [{"b": False}]}),
    ({"a": 1}, {"a": 1, "b": None}), (Decimal("1"), Decimal("1.0000000000000001")), (Decimal("1"), 1),
)


class JsonValuesTests(unittest.TestCase):
    def test_types_are_distinct_at_every_depth(self):
        for left, right in DIFFERENT:
            with self.subTest(left=left, right=right):
                self.assertFalse(same_document(left, right))
                self.assertFalse(same_document(right, left))
                self.assertNotEqual(document_key(left), document_key(right))

    def test_equal_data_is_the_same(self):
        for value in (None, True, 0, 1.5, "x", [1, "a"], {"a": [1, {"b": True}]}, Decimal("2.0")):
            with self.subTest(value=value):
                self.assertTrue(same_document(value, copy.deepcopy(value)))
        # Member order is not JSON data; an array and a tuple are arrays.
        self.assertTrue(same_document({"a": 1, "b": 2}, {"b": 2, "a": 1}))
        self.assertTrue(same_document([("a", 1)], [["a", 1]]))

    def test_anything_else_is_refused(self):
        for value in (object(), {1, 2}, b"x", Path("x")):
            with self.subTest(value=value), self.assertRaises(TypeError):
                document_key(value)


def nested(depth, leaf, kind="object"):
    value = leaf
    for _ in range(depth):
        value = {"a": value} if kind == "object" else [value]
    return value


class ScaleTests(unittest.TestCase):
    """Deep and wide documents are compared without recursion and in about
    linear time: an unchanged document of 10,000 levels is the same, and a
    leaf of another type at the bottom is found."""

    def assertFast(self, started, seconds):
        self.assertLess(time.perf_counter() - started, seconds)

    def test_deep_documents(self):
        for kind in ("object", "array"):
            with self.subTest(kind=kind):
                started = time.perf_counter()
                self.assertTrue(same_document(nested(10_000, 1, kind), nested(10_000, 1, kind)))
                self.assertFalse(same_document(nested(10_000, 1, kind), nested(10_000, True, kind)))
                self.assertEqual(document_key(nested(10_000, 1, kind)), document_key(nested(10_000, 1, kind)))
                self.assertNotEqual(document_key(nested(10_000, 1, kind)), document_key(nested(10_000, 1.0, kind)))
                hash(document_key(nested(10_000, 1, kind)))
                self.assertFast(started, 5)

    def test_wide_documents(self):
        wide = {f"k{index}": [index, {"v": [True, None, "x"] * 10}] for index in range(20_000)}
        started = time.perf_counter()
        self.assertTrue(same_document(wide, copy.deepcopy(wide)))
        changed = copy.deepcopy(wide)
        changed["k19999"][1]["v"][0] = 1
        self.assertFalse(same_document(wide, changed))
        self.assertEqual(document_key(wide), document_key(copy.deepcopy(wide)))
        self.assertNotEqual(document_key(wide), document_key(changed))
        self.assertFast(started, 10)

    def test_the_immutability_guard_on_deep_documents(self):
        for depth in (400, 10_000):
            with self.subTest(depth=depth):
                started = time.perf_counter()
                self.assertEqual(immutability.document_changes(
                    "vectors/x.json", nested(depth, 1), nested(depth, 1)), [])
                self.assertEqual(immutability.document_changes(
                    "vectors/x.json", nested(depth, 1), nested(depth, True)), ["document changed"])
                def schema(leaf):
                    value = {"type": leaf}
                    for _ in range(depth):
                        value = {"not": value, "description": "d"}
                    return value

                self.assertEqual(immutability.document_changes(
                    "schemas/x-v1.schema.json", schema("object"), schema("object")), [])
                self.assertEqual(immutability.document_changes(
                    "schemas/x-v1.schema.json", schema("object"), schema("array")), ["assertions changed"])
                schema = schema("object")
                self.assertEqual(len(immutability.digest(immutability.assertions(schema))), 64)
                self.assertFast(started, 10)


class DecimalValueTests(unittest.TestCase):
    """Decimals compare by exact value (COMPATIBILITY.md: a respelling that
    cannot change validation is not a change): `1.0 == 1.00 == 1e0`, while
    an integer stays another value and `1.0000000000000001` another number."""

    def test_spellings_of_one_value(self):
        parse = immutability.strict_json
        for one, other in (("1.0", "1.00"), ("1.0", "1e0"), ("1.0", "10E-1"), ("0.0", "-0.0"), ("2.50", "25e-1"),
                           ("1.5e300", "15E299")):
            with self.subTest(one=one, other=other):
                left, right = parse(one, "x"), parse(other, "x")
                self.assertTrue(same_schema_value(left, right))
                self.assertEqual(schema_value_key(left), schema_value_key(right))
        self.assertEqual(immutability.document_changes(
            "schemas/x-v1.schema.json", parse('{"minimum": 1.0}', "x"), parse('{"minimum": 1.00}', "x")), [])
        # A vector keeps the exact representation of its numbers.
        self.assertEqual(immutability.document_changes(
            "vectors/x.json", parse('[1e0]', "x"), parse('[1.0]', "x")), ["document changed"])

    def test_other_values_stay_other(self):
        parse = immutability.strict_json
        for one, other in (("1", "1.0"), ("1.0", "1.0000000000000001"), ("1.0", "-1.0"), ("1e2", "1e3"),
                           ("0.1", "0.10000000000000000000000000000001")):
            with self.subTest(one=one, other=other):
                left, right = parse(one, "x"), parse(other, "x")
                self.assertFalse(same_schema_value(left, right))
                self.assertNotEqual(schema_value_key(left), schema_value_key(right))
                self.assertNotEqual(immutability.digest(left), immutability.digest(right))
        self.assertEqual(immutability.document_changes(
            "schemas/x-v1.schema.json", parse('{"minimum": 1}', "x"), parse('{"minimum": 1.0}', "x")),
            ["assertions changed"])


class TwoContextsTests(unittest.TestCase):
    """A numeric assertion of a schema is compared by value (JSON Schema
    compares numbers by value: `0.0` and `-0.0`, `1.0` and `1.00` validate
    the same instances); a published document that is not a schema
    assertion (a vector, an example, a catalog) is compared by the exact
    representation of each number (COMPATIBILITY.md: published vectors are
    not modified), so the sign of a zero and the written digits count."""

    def test_the_reported_negative_zero_of_a_vector(self):
        relative = "vectors/rest-arrow-adapter-v1/float-at-the-overflow-boundary.json"
        text = (ROOT / relative).read_text(encoding="utf-8")
        # Only the numbers (lines 34 and 62), not the description.
        self.assertEqual(text.count('"v": -0.0'), 2)
        before = immutability.strict_json(text, relative)
        after = immutability.strict_json(text.replace('"v": -0.0', '"v": 0.0'), relative)
        self.assertEqual(immutability.document_changes(relative, before, after), ["document changed"])

    def test_negative_zero_in_a_schema_and_in_a_vector(self):
        parse = immutability.strict_json
        schema = '{"type": "number", "minimum": %s, "const": %s}'
        self.assertEqual(immutability.document_changes(
            "schemas/x-v1.schema.json", parse(schema % ("-0.0", "-0.0"), "x"), parse(schema % ("0.0", "0.0"), "x")),
            [])
        for one, other in (("-0.0", "0.0"), ("1.0", "1.00"), ("2.5", "2.50")):
            with self.subTest(one=one, other=other):
                self.assertEqual(immutability.document_changes(
                    "vectors/x.json", parse('{"v": %s}' % one, "x"), parse('{"v": %s}' % other, "x")),
                    ["document changed"])
                self.assertFalse(same_document(parse(one, "x"), parse(other, "x")))
                self.assertNotEqual(document_key(parse(one, "x")), document_key(parse(other, "x")))
                self.assertTrue(same_schema_value(parse(one, "x"), parse(other, "x")))
                self.assertEqual(schema_value_key(parse(one, "x")), schema_value_key(parse(other, "x")))
        # No spelling is tolerated in a document: the number's own text.
        for one, other in (("-0.0", "-0e-1"), ("1.0", "10e-1"), ("1e0", "1E0"), ("-0", "0")):
            with self.subTest(one=one, other=other):
                self.assertFalse(same_document(parse(one, "x"), parse(other, "x")))
                self.assertNotEqual(document_key(parse(one, "x")), document_key(parse(other, "x")))
        # A catalog is a document too.
        catalog = json.loads((ROOT / "catalogs/database-tools-v1.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(catalog)
        before["operations"][0]["attributes"] = {"limit": parse("-0.0", "x")}
        after = copy.deepcopy(catalog)
        after["operations"][0]["attributes"] = {"limit": parse("0.0", "x")}
        self.assertTrue(immutability.catalog_changes(before, after))
        # Floats (the validator's own parser): the sign of a zero counts in
        # a document.
        self.assertFalse(same_document(-0.0, 0.0))
        self.assertTrue(same_schema_value(-0.0, 0.0))

    def test_the_digests_follow_the_comparisons(self):
        """A document's erratum digest is that of its bytes; a schema's, that
        of its assertions by value."""
        digest = immutability.erratum_digest
        for one, other in (("-0.0", "0.0"), ("-0.0", "-0e-1"), ("1.0", "1.00"), ("1.0", "10e-1")):
            with self.subTest(one=one, other=other):
                self.assertNotEqual(digest("vectors/x.json", b'[%s]' % one.encode()),
                                    digest("vectors/x.json", b'[%s]' % other.encode()))
                self.assertEqual(digest("schemas/x-v1.schema.json", b'{"minimum": %s}' % one.encode()),
                                 digest("schemas/x-v1.schema.json", b'{"minimum": %s}' % other.encode()))
        self.assertNotEqual(digest("schemas/x-v1.schema.json", b'{"minimum": 1}'),
                            digest("schemas/x-v1.schema.json", b'{"minimum": 1.0}'))


class PublishedBytesTests(unittest.TestCase):
    """A published document that is not a schema is compared by its bytes
    (line ends normalized, as `.gitattributes` stores them): no parsing, no
    spelling tolerated. Catalogs, registries and bindings, which may grow,
    compare their entries with each number's exact text. Schemas compare
    their assertions by value."""

    def test_vectors_by_their_bytes(self):
        changes = immutability.published_changes
        for one, other in (("-0.0", "-0e-1"), ("1.0", "10e-1"), ("-0.0", "0.0"), ("1.0", "1.00")):
            with self.subTest(one=one, other=other):
                self.assertEqual(changes("vectors/x.json", b'{"v": %s}\n' % one.encode(),
                                         b'{"v": %s}\n' % other.encode()), ["document changed"])
        self.assertEqual(changes("vectors/x.json", b'{"v": 1}\n', b'{"v":  1}\n'), ["document changed"])
        self.assertEqual(changes("vectors/x.json", b'{"v": 1}\n', b'{"v": 1}\r\n'), [])
        self.assertEqual(changes("vectors/y/x.json", b'[1.0]', b'[1.0]'), [])
        # Examples are not published documents (COMPATIBILITY.md): unguarded.
        self.assertFalse(immutability.is_protected("examples/valid/x.json"))
        self.assertTrue(immutability.is_protected("vectors/y/x.json"))

    def test_schemas_by_value(self):
        changes = immutability.published_changes
        for one, other in (("-0.0", "-0e-1"), ("1.0", "10e-1"), ("1.0", "1.00")):
            with self.subTest(one=one, other=other):
                self.assertEqual(changes("schemas/x-v1.schema.json", b'{"minimum": %s}' % one.encode(),
                                         b'{"minimum": %s}' % other.encode()), [])
        self.assertEqual(changes("schemas/x-v1.schema.json", b'{"minimum": 1}', b'{"minimum": 1.0}'),
                         ["assertions changed"])

    def test_catalog_entries_by_exact_text(self):
        text = (ROOT / "catalogs/database-tools-v1.json").read_text(encoding="utf-8")
        catalog = json.loads(text)
        catalog["operations"][0]["attributes"] = {"limit": "@"}
        base = json.dumps(catalog, indent=2)
        for one, other in (("-0.0", "-0e-1"), ("1.0", "10e-1"), ("1.0", "1.0000000000000001")):
            with self.subTest(one=one, other=other):
                before = base.replace('"@"', one).encode()
                after = base.replace('"@"', other).encode()
                self.assertTrue(immutability.published_changes("catalogs/database-tools-v1.json", before, after))
        self.assertEqual(immutability.published_changes(
            "catalogs/database-tools-v1.json", base.encode(), json.dumps(json.loads(base)).encode()), [])

    def test_the_errata_digests(self):
        for relative, erratum in immutability.ERRATA.items():
            with self.subTest(relative):
                data = (ROOT / relative).read_bytes()
                self.assertEqual(immutability.erratum_digest(relative, data), erratum.after)


class IntegerLiteralTests(unittest.TestCase):
    """`-0` is an integer literal: every consumer reads it as the integer 0
    (an `int`), while the exact text stays for the immutability of a
    document; `0.0`, `-0.0` and `0e0` are decimals."""

    def test_minus_zero_is_an_integer(self):
        value = validator.loads_json("-0")
        self.assertIsInstance(value, int)
        self.assertNotIsInstance(value, bool)
        self.assertEqual(value, 0)
        for text in ("0.0", "-0.0", "0e0"):
            with self.subTest(text):
                self.assertNotIsInstance(validator.loads_json(text), int)
        # Exact text in a document, by value in a schema.
        self.assertFalse(same_document(validator.loads_json("-0"), validator.loads_json("0")))
        self.assertTrue(same_schema_value(validator.loads_json("-0"), validator.loads_json("0")))
        self.assertTrue(immutability.published_changes(
            "catalogs/x-v1.json",
            b'{"contract": "plenora-operation-registry-v1", "operations": [{"id": "a", "n": -0}]}',
            b'{"contract": "plenora-operation-registry-v1", "operations": [{"id": "a", "n": 0}]}'))
        self.assertEqual(validator.compact_json_size(validator.loads_json('{"a": -0}')), len('{"a":-0}'))
        import gate_fuzz
        gate = gate_fuzz.Gate()
        self.assertNotEqual(gate._content(validator.loads_json("[-0]")), gate._content(validator.loads_json("[0]")))
        # The arrow-data rows read it as an integer too.
        import arrow_data
        self.assertIsNone(arrow_data._cell(0, {"type": "int64", "nullable": False}, validator.loads_json("-0")))


class CatalogVersionsTests(unittest.TestCase):
    """The validator parses numbers exactly, and a repeated identity is
    compared with the version just before it."""

    def versions(self, *attributes):
        def catalog(value):
            return {"operations": [{
                "id": "a.b", "version": 1, "requirement": "required", "input": {}, "output": {},
                "side_effect": "none", "controls": {}, "surfaces": ["rust"], "attributes": {"x": value}}]}
        return {"c": {index + 1: catalog(value) for index, value in enumerate(attributes)}}

    def test_exact_numbers_from_the_parser(self):
        for one, other in (("1.0", "1.0000000000000001"), ("1.0", "1.00"), ("-0.0", "0.0"), ("1.0", "10e-1")):
            with self.subTest(one=one, other=other):
                left, right = validator.loads_json(one), validator.loads_json(other)
                self.assertFalse(same_document(left, right))
                self.assertEqual(len(validator.repeated_identity_errors(self.versions(left, right))), 1)
        self.assertEqual(validator.repeated_identity_errors(
            self.versions(validator.loads_json("1.0"), validator.loads_json("1.0"))), [])

    def test_each_version_against_the_one_before(self):
        # v2 changes the attribute once; v3 keeps v2's value: one change.
        self.assertEqual(len(validator.repeated_identity_errors(self.versions(1, 2, 2))), 1)
        self.assertEqual(len(validator.repeated_identity_errors(self.versions(1, 2, 3))), 2)


class BoundedMemoryTests(unittest.TestCase):
    def test_the_difference_path_in_linear_memory(self):
        import tracemalloc
        import rest_adapter
        depth = 8_000
        left, right = 1, 2
        for _ in range(depth):
            left, right = {"k": [left]}, {"k": [right]}
        tracemalloc.start()
        try:
            path = rest_adapter.difference(left, right)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(path.count("/"), 2 * depth)
        # Linear: about 1.4 KiB per level (11 MiB here); the quadratic walk
        # took over 300 MiB under tracemalloc.
        self.assertLess(peak, 32 * 2**20)

    def test_the_cache_key_of_a_deep_document(self):
        import gate_fuzz
        gate = gate_fuzz.Gate()
        for depth in (1_100, 10_000):
            with self.subTest(depth=depth):
                self.assertEqual(gate._content(nested(depth, 1)), gate._content(nested(depth, 1)))
                self.assertNotEqual(gate._content(nested(depth, 1)), gate._content(nested(depth, True)))
                self.assertNotEqual(gate._content({"a": 1, "b": 2}), gate._content({"b": 2, "a": 1}))


class DeepTraversalTests(unittest.TestCase):
    """The traversals of the gate read documents deeper than the recursion
    limit (1,100 and 10,000 levels) without recursion, in document order."""

    def test_members_and_items(self):
        import gate_fuzz
        import rest_adapter
        for depth in (1_100, 10_000):
            with self.subTest(depth=depth):
                document = nested(depth, "leaf", "object")
                self.assertEqual(sum(1 for _ in gate_fuzz.members(document)), depth)
                self.assertEqual(sum(1 for _ in validator.nested_items(document)), depth)
                self.assertEqual(list(validator.artifact_strings(document)), ["leaf"])
                array = nested(depth, "leaf", "array")
                self.assertEqual(list(validator.artifact_strings(array)), ["leaf"])
                self.assertEqual(sum(1 for _ in gate_fuzz.members(array)), depth)
                left, right = nested(depth, 1, "object"), nested(depth, 2, "object")
                self.assertEqual(rest_adapter.difference(left, right).count("/"), depth)

    def test_error_bounds_of_deep_details(self):
        for depth in (1_100, 10_000):
            with self.subTest(depth=depth):
                error = {"category": "internal", "message": "m", "details": nested(depth, "leaf", "object")}
                self.assertIn("error details exceed the nesting-depth limit", validator.error_bound_errors(error))

    def test_compact_size_is_the_size_of_the_compact_text(self):
        for value in ({"a": [1, 1.5, None, True, "é\u0000"], 1: {}, None: [], True: "x"}, [], {}, "s", 1e300,
                      json.loads((ROOT / "examples/valid/cli-error.json").read_text(encoding="utf-8"))):
            with self.subTest(value=value):
                self.assertEqual(validator.compact_json_size(value),
                                 len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))

    def test_document_order_is_kept(self):
        import gate_fuzz
        document = {"a": [1, {"b": "x"}], "c": {"d": "y", "e": ["z"]}}
        self.assertEqual(list(gate_fuzz.members(document)),
                         [("a",), ("a", 0), ("a", 1), ("a", 1, "b"), ("c",), ("c", "d"), ("c", "e"), ("c", "e", 0)])
        self.assertEqual(list(validator.nested_items(document)),
                         [("a", [1, {"b": "x"}]), ("b", "x"), ("c", {"d": "y", "e": ["z"]}), ("d", "y"), ("e", ["z"])])
        self.assertEqual(list(validator.artifact_strings(document)), ["x", "y", "z"])
        self.assertEqual(list(validator.artifact_strings("s")), ["s"])


class StrictJsonTests(unittest.TestCase):
    """Numbers are parsed exactly: `1.0` and `1.0000000000000001` are two
    values, which a binary float would make one."""

    def test_numbers_keep_their_exact_value(self):
        parse = immutability.strict_json
        self.assertFalse(same_document(parse('{"a": 1.0}', "x"), parse('{"a": 1.0000000000000001}', "x")))
        self.assertEqual(immutability.document_changes(
            "vectors/x.json", parse('{"a": 1.0}', "x"), parse('{"a": 1.0000000000000001}', "x")),
            ["document changed"])
        self.assertIs(type(parse("1", "x")), int)
        self.assertFalse(same_document(parse("1", "x"), parse("1.0", "x")))
        self.assertTrue(same_document(parse('{"a": 2.5}', "x"), parse('{"a": 2.5}', "x")))

    def test_constants_that_are_not_json_are_refused(self):
        for text in ("NaN", "Infinity", "-Infinity", '{"a": NaN}'):
            with self.subTest(text), self.assertRaises(ValueError):
                immutability.strict_json(text, "x")

    def test_the_digest_of_a_float_free_document_is_unchanged(self):
        """The published errata digests stay valid: without floats, the
        canonical text is the one `json.dumps` gave."""
        import hashlib
        document = {"b": [1, True, None, "é\u0000\"x"], "a": {"z": False, "y": -3}}
        expected = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(immutability.digest(document), expected)
        self.assertNotEqual(immutability.digest(immutability.strict_json('{"a": 1.0}', "x")),
                            immutability.digest(immutability.strict_json('{"a": 1.0000000000000001}', "x")))


class ImmutabilityTests(unittest.TestCase):
    """A published document changed from `1` to `true` or `1.0` is changed."""

    def test_schema_assertions(self):
        before = {"type": "object", "properties": {"schema_version": {"const": 1}}}
        for after_value in (True, 1.0):
            after = copy.deepcopy(before)
            after["properties"]["schema_version"]["const"] = after_value
            with self.subTest(after_value):
                self.assertEqual(immutability.document_changes("schemas/x-v1.schema.json", before, after),
                                 ["assertions changed"])
        self.assertEqual(immutability.document_changes("schemas/x-v1.schema.json", before, copy.deepcopy(before)), [])

    def test_whole_documents(self):
        for left, right in DIFFERENT[:5]:
            with self.subTest(left=left, right=right):
                self.assertEqual(immutability.document_changes("vectors/x.json", {"v": left}, {"v": right}),
                                 ["document changed"])

    def catalog(self):
        return json.loads((ROOT / "catalogs/database-tools-v1.json").read_text(encoding="utf-8"))

    def test_catalog_identity_and_fields(self):
        before = self.catalog()
        self.assertEqual(immutability.catalog_changes(before, copy.deepcopy(before)), [])
        renumbered = copy.deepcopy(before)
        renumbered["operations"][0]["version"] = True
        self.assertTrue(any("removed" in error for error in immutability.catalog_changes(before, renumbered)))
        controls = copy.deepcopy(before)
        controls["operations"][0]["controls"]["cancellation"] = 1
        self.assertTrue(any("changes controls" in error for error in immutability.catalog_changes(before, controls)))
        schema_version = copy.deepcopy(before)
        schema_version["schema_version"] = 1.0
        self.assertIn("catalog changes schema_version", immutability.catalog_changes(before, schema_version))

    def test_registry_entries(self):
        before = {"contract": "plenora-operation-registry-v1", "operations": [{"id": "geo.x", "arity": 1}]}
        after = copy.deepcopy(before)
        after["operations"][0]["arity"] = True
        self.assertEqual(immutability.registry_changes(before, after), ["kernel geo.x changes"])

    def test_binding_entries(self):
        section = {"component": "c", "artifact": None, "discovery": [],
                   "bindings": [{"operation": "a.b", "version": 1, "requirement": "required", "entrypoints": ["x"]}]}
        before = {"contract": "plenora-surface-bindings-v1", "components": [section]}
        after = copy.deepcopy(before)
        after["components"][0]["bindings"][0]["version"] = True
        self.assertIn("c binding a.b@1 removed", immutability.binding_changes(before, after))


class ValidatorTests(unittest.TestCase):
    def test_a_repeated_identity_keeps_its_attributes_by_type(self):
        versions = validator.load_catalog_versions()
        component = next(name for name, by_version in versions.items() if len(by_version) > 1)
        by_version = copy.deepcopy(versions[component])
        first, last = min(by_version), max(by_version)
        shared = {(item["id"], item["version"]) for item in by_version[first]["operations"]} & {
            (item["id"], item["version"]) for item in by_version[last]["operations"]}
        self.assertTrue(shared)
        identity = sorted(shared)[0]
        for catalog in (by_version[first], by_version[last]):
            for item in catalog["operations"]:
                if (item["id"], item["version"]) == identity:
                    item.setdefault("attributes", {})["zz_flag"] = 1 if catalog is by_version[first] else True
        self.assertEqual(validator.repeated_identity_errors({component: by_version}).__len__(), 1)

    def test_differing_members_by_type(self):
        self.assertEqual(messages.differing_members({"a": 1, "b": 0}, {"a": True, "b": 0.0}, {"a", "b"}), "a, b")
        self.assertEqual(messages.differing_members({"a": None}, {}, {"a"}), "a")

    def test_an_adoption_artifact_by_type(self):
        document = json.loads((ROOT / "examples/valid/adoption-manifest-v4.json").read_text(encoding="utf-8"))
        artifact = document["artifacts"][0]
        number = next((key for key, value in artifact.items() if type(value) in (int, bool)), None)
        repeated = copy.deepcopy(artifact)
        if number is None:
            number = "zz_number"
            artifact[number] = 1
        repeated[number] = True if artifact[number] is not True else 1
        document["artifacts"].append(repeated)
        self.assertTrue(any("ambiguous artifact" in error for error in adoption_errors(document)))


if __name__ == "__main__":
    unittest.main()
