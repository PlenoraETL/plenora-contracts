"""Arrow Primary Geometry 1.0: the key, its form, the operand and GeoParquet."""

import copy
import unittest

import arrow_data
import arrow_primary as primary
import interop_vectors as interop
import validate_specs as validator
from test_interop_vectors import KERNELS, gate_inputs

ROOT = validator.ROOT
ARROW = ROOT / "vectors/arrow-primary-v1"
INTEROP = ROOT / "vectors/interop-primary-v1"
GEOPARQUET = ROOT / "vectors/geoparquet-primary-v1"
SECRET = "SECRET_VALUE"


def arrow(name):
    return validator.load_json(ARROW / name)


def with_key(table, value):
    table = copy.deepcopy(table)
    if value is None:
        table["schema_metadata"].pop(primary.KEY, None)
    else:
        table["schema_metadata"][primary.KEY] = value
    return table


def interop_errors(name, document=None):
    document = document or validator.load_json(INTEROP / name)
    return interop.vector_errors(INTEROP / name, document, *gate_inputs(), KERNELS, True)


class KeyTests(unittest.TestCase):
    def setUp(self):
        self.two = arrow("primary-second-of-two.json")

    def test_grammar_of_the_value(self):
        for value in ("", "02", "+2", "2 ", "2\n", "-1", "position", "None", "NONE", "1.0"):
            with self.subTest(value=value):
                self.assertEqual(primary.verdict(with_key(self.two, value)), ("schema", "PRIM-001"))
        for value in ("1", "2", "none"):
            with self.subTest(value=value):
                self.assertIsNone(primary.verdict(with_key(self.two, value)))

    def test_reference_must_name_a_geometry_field(self):
        for value in ("0", "3", "18446744073709551616"):
            with self.subTest(value=value):
                self.assertEqual(primary.verdict(with_key(self.two, value)), ("schema", "PRIM-003"))

    def test_key_without_geometry_is_not_conforming(self):
        table = arrow("invalid-primary-without-geometry.json")
        for value in ("none", "0", "1"):
            with self.subTest(value=value):
                self.assertEqual(primary.verdict(with_key(table, value)), ("schema", "PRIM-003"))
        self.assertIsNone(primary.verdict(with_key(table, None)))

    def test_key_in_field_metadata(self):
        table = copy.deepcopy(self.two)
        table["fields"][0]["metadata"][primary.KEY] = "2"
        self.assertEqual(primary.verdict(table), ("schema", "PRIM-001"))

    def test_resolved_against_the_schema_as_received(self):
        table = copy.deepcopy(self.two)
        del table["fields"][2]["metadata"]["plenora.field_id"]
        completed = copy.deepcopy(table)
        interop.assign_field_ids(completed)
        # The identity the consumer assigns is not one the producer named.
        self.assertEqual(primary.schema_verdict(completed, table), ("schema", "PRIM-003"))
        self.assertIsNone(primary.schema_verdict(completed))

    def test_state(self):
        two, one = self.two, arrow("primary-explicit-one-geometry.json")
        self.assertEqual(primary.primary(two)["name"], "position")
        self.assertEqual(primary.primary(with_key(two, "1"))["name"], "track")
        self.assertIsNone(primary.primary(with_key(two, None)))
        self.assertIsNone(primary.primary(with_key(two, "none")))
        self.assertEqual(primary.primary(with_key(one, None))["name"], "position")
        self.assertIsNone(primary.primary(with_key(one, "none")))

    def test_canonical_form(self):
        two, one = self.two, arrow("primary-explicit-one-geometry.json")
        cases = [
            (two, "2", "2"), (two, None, None), (two, "none", None),
            (one, "1", None), (one, None, None), (one, "none", "none"),
        ]
        for table, value, emitted in cases:
            with self.subTest(value=value, fields=len(table["fields"])):
                table = with_key(table, value)
                primary.canonical(table)
                self.assertEqual(table["schema_metadata"].get(primary.KEY), emitted)

    def test_every_published_arrow_data_vector_keeps_its_verdict(self):
        for path in sorted((ROOT / "vectors/arrow-data-v1").glob("*.json")):
            with self.subTest(path=path.name):
                vector = validator.load_json(path)
                self.assertEqual(primary.verdict(vector), arrow_data.verdict(vector))

    def test_vector_with_the_wrong_rule_is_refused(self):
        vector = arrow("invalid-primary-dangling.json")
        vector["rules"] = ["PRIM-001"]
        self.assertEqual(primary.vector_errors(vector), ["does not cite PRIM-003, the rule that rejects it"])
        vector = arrow("primary-second-of-two.json")
        vector["schema_metadata"][primary.KEY] = "0"
        self.assertEqual(primary.vector_errors(vector), ["must be accepted, but PRIM-003 rejects it with schema"])

    def test_messages_carry_no_data(self):
        vector = with_key(arrow("invalid-primary-dangling.json"), SECRET)
        vector["fields"][2]["name"] = SECRET
        for row in vector["rows"]:
            row[SECRET] = row.pop("position")
        self.assertFalse(any(SECRET in error for error in primary.vector_errors(vector)))


class OperandTests(unittest.TestCase):
    def test_selection(self):
        two = arrow("primary-second-of-two.json")
        self.assertEqual([field["name"] for field in primary.operands(two, None)], ["position"])
        self.assertEqual([field["name"] for field in primary.operands(two, "1")], ["track"])
        for selection in ("0", "9"):
            self.assertEqual(primary.operands(two, selection), ("schema", "PRIM-007"))
        self.assertEqual(primary.operands(with_key(two, None), None), ("schema", "PRIM-007"))
        one = arrow("primary-none-one-geometry.json")
        self.assertEqual(primary.operands(one, None), ("schema", "PRIM-007"))
        self.assertEqual([field["name"] for field in primary.operands(one, "1")], ["position"])

    def test_selection_before_completion_and_rejection_precedence(self):
        table = arrow("missing-geometry-identities.json")
        geo = {"component": "plenora-data-tools", "operation": "data.run", "version": 2,
               "params": {"plan": "geo.centroid", "geometry": "1"}, "transformations": []}
        for reverse in (False, True):
            if reverse:
                table["fields"][1:] = reversed(table["fields"][1:])
            self.assertEqual(interop.step_rejection(table, geo, KERNELS, True),
                             ("operation", "schema", "PRIM-007"))
        geo["params"]["limits"] = ["one_geometry_field"]
        self.assertEqual(interop.step_rejection(table, geo, KERNELS, True),
                         ("support", "unsupported", "GEO-012"))

    def test_received_operand_uses_completed_metadata(self):
        table = arrow("primary-second-of-two.json")
        del table["fields"][2]["metadata"]["plenora.geometry.spatial_semantics"]
        geo = {"component": "plenora-data-tools", "operation": "data.run", "version": 2,
               "params": {"plan": "geo.centroid", "geometry": "2"}, "transformations": []}
        self.assertIsNone(interop.step_rejection(table, geo, KERNELS, True))

    def test_a_secondary_crs_does_not_decide(self):
        """GEO-015 on the operand only: under Arrow Geometry Semantics 1.0
        alone the unknown CRS of the secondary decides first."""
        name = "rejection-primary-truncated-secondary-unknown-crs-geo-operation.json"
        vector = validator.load_json(INTEROP / name)
        table = validator.load_json((INTEROP / vector["input"]).resolve())
        step = vector["chain"][0]
        self.assertEqual(interop.step_rejection(table, step, KERNELS, True), ("input", "data_mapping", "GEO-011"))
        self.assertEqual(interop.step_rejection(table, step, KERNELS), ("crs", "crs", "GEO-015"))

    def test_selected_secondary_brings_its_crs(self):
        table = arrow("primary-secondary-unknown-crs.json")
        geo = {"component": "plenora-data-tools", "operation": "data.run", "version": 2,
               "params": {"plan": "geo.centroid"}, "transformations": []}
        self.assertIsNone(interop.step_rejection(table, geo, KERNELS, True))
        geo["params"]["geometry"] = "1"
        self.assertEqual(interop.step_rejection(table, geo, KERNELS, True), ("crs", "crs", "GEO-015"))

    def test_support_limit_before_the_missing_operand(self):
        table = validator.load_json(ROOT / "vectors/arrow-data-v1/two-geometry-fields.json")
        geo = {"component": "plenora-data-tools", "operation": "data.run", "version": 2,
               "params": {"plan": "geo.centroid", "limits": ["one_geometry_field"]}, "transformations": []}
        self.assertEqual(interop.step_rejection(table, geo, KERNELS, True), ("support", "unsupported", "GEO-012"))
        del geo["params"]["limits"]
        self.assertEqual(interop.step_rejection(table, geo, KERNELS, True), ("operation", "schema", "PRIM-007"))


class InteropTests(unittest.TestCase):
    def test_published_vectors(self):
        for path in sorted(INTEROP.glob("*.json")):
            with self.subTest(path=path.name):
                self.assertEqual(interop_errors(path.name), [])

    def test_no_promotion_along_the_chain(self):
        name = "handoff-io-data-io-no-primary.json"
        vector = validator.load_json(INTEROP / name)
        vector["expected_output"]["schema_metadata"][primary.KEY] = "1"
        self.assertTrue(interop_errors(name, vector))
        name = "handoff-io-data-io-primary-none-one-geometry.json"
        vector = validator.load_json(INTEROP / name)
        del vector["expected_output"]["schema_metadata"][primary.KEY]
        self.assertTrue(interop_errors(name, vector))

    def test_lost_key_is_a_defect(self):
        name = "handoff-io-data-io-primary-second.json"
        vector = validator.load_json(INTEROP / name)
        del vector["expected_output"]["schema_metadata"][primary.KEY]
        self.assertTrue(interop_errors(name, vector))

    def test_selection_parameter_is_checked(self):
        name = "rejection-selection-not-geometry-geo-operation.json"
        for value, rule in ((1, "field identity"), ("02", "field identity"), ("position", "field identity")):
            with self.subTest(value=value):
                vector = validator.load_json(INTEROP / name)
                vector["chain"][0]["params"]["geometry"] = value
                errors = interop_errors(name, vector)
                self.assertTrue(errors and all(rule in error for error in errors), errors)
        name = "rejection-dangling-primary-data-run.json"
        vector = validator.load_json(INTEROP / name)
        vector["chain"][0]["params"]["geometry"] = "1"
        self.assertIn("step 1 selects a geometry but does not compute (PRIM-007)", interop_errors(name, vector))

    def test_operation_class_category(self):
        name = "rejection-no-primary-geo-operation.json"
        vector = validator.load_json(INTEROP / name)
        vector["expected_error"]["category"] = "unsupported"
        self.assertIn("class operation is schema (REJ-001)", interop_errors(name, vector))

    def test_published_interop_vectors_unchanged_by_the_flag(self):
        """Every vector of interop-v1 keeps its verdict under the contract:
        none names the key, and every step that computes there has one
        geometry field, its primary (PRIM-002)."""
        for path in sorted((ROOT / "vectors/interop-v1").glob("*.json")):
            with self.subTest(path=path.name):
                vector = validator.load_json(path)
                self.assertEqual(interop.vector_errors(path, vector, *gate_inputs(), KERNELS, True), [])


class GeoParquetTests(unittest.TestCase):
    def vector(self, name):
        vector = validator.load_json(GEOPARQUET / name)
        return vector, validator.load_json((GEOPARQUET / vector["table"]).resolve())

    def test_published_vectors(self):
        for path in sorted(GEOPARQUET.glob("*.json")):
            with self.subTest(path=path.name):
                self.assertEqual(primary.geoparquet_errors(*self.vector(path.name)), [])

    def test_writer_names_the_primary_and_every_column(self):
        vector, table = self.vector("write-primary-second.json")
        vector["geo"]["primary_column"] = "track"
        self.assertEqual(primary.geoparquet_errors(vector, table),
                         ["primary_column does not name the primary field (PRIM-008)"])
        vector, table = self.vector("write-primary-second.json")
        vector["geo"]["columns"] = ["position"]
        self.assertEqual(primary.geoparquet_errors(vector, table),
                         ["columns do not list every geometry field in field order (PRIM-008)"])

    def test_writer_never_chooses(self):
        vector, table = self.vector("write-no-primary.json")
        del vector["expected_error"]
        vector["geo"] = {"primary_column": "geometry", "columns": ["geometry", "site"]}
        self.assertEqual(primary.geoparquet_errors(vector, table),
                         ["a table without a primary is written only as a rejection (PRIM-008)"])

    def test_reader_delivers_the_named_primary_in_canonical_form(self):
        vector, table = self.vector("read-primary-second.json")
        vector["geo"]["primary_column"] = "track"
        self.assertEqual(primary.geoparquet_errors(vector, table),
                         ["the delivered primary is not the field primary_column names (PRIM-008)"])
        vector, table = self.vector("read-one-geometry.json")
        table["schema_metadata"][primary.KEY] = "1"
        self.assertEqual(primary.geoparquet_errors(vector, table),
                         ["the delivered key is not in the form PRIM-004 emits"])

    def test_gate(self):
        self.assertEqual(validator.validate_geoparquet_primary_vectors(), [])
        self.assertEqual(validator.validate_arrow_primary_vectors(), [])


class CompositionTests(unittest.TestCase):
    def test_vectors_and_wrong_expectations(self):
        for path in sorted((ROOT / "vectors/primary-composition-v1").glob("*.json")):
            with self.subTest(path=path.name):
                vector = validator.load_json(path)
                self.assertEqual(primary.composition_errors(vector), [])
                for key in ("expected_primary", "expected_key"):
                    changed = copy.deepcopy(vector)
                    changed[key] = "999"
                    self.assertTrue(primary.composition_errors(changed))

    def test_invalid_provenance(self):
        path = ROOT / "vectors/primary-composition-v1/join-preserves-remapped-primary.json"
        for mutation in ("input", "field", "duplicate", "primary", "output"):
            with self.subTest(mutation=mutation):
                vector = validator.load_json(path)
                if mutation == "duplicate":
                    vector["mapping"].append(copy.deepcopy(vector["mapping"][0]))
                elif mutation == "primary":
                    vector["inputs"][0]["primary"] = "999"
                elif mutation == "output":
                    vector["mapping"][0]["output"] = vector["mapping"][1]["output"]
                else:
                    vector["mapping"][0][mutation] = 999 if mutation == "input" else "999"
                self.assertTrue(primary.composition_errors(vector))


if __name__ == "__main__":
    unittest.main()
