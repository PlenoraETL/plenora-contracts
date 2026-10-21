"""Decision 0022: identity across a store and the optional mixed type list."""

import copy
import unittest

import arrow_data
import interop_vectors as interop
import validate_specs as validator
from test_interop_vectors import errors_of, gate_inputs, KERNELS


class Decision0022Tests(unittest.TestCase):
    def assignment(self):
        path = validator.ROOT / "vectors/interop-assignment-v1/handoff-store-assigned-field-id.json"
        vector = validator.load_json(path)
        table = validator.load_json(path.parent / vector["input"])
        return path, vector, table, interop.expected_output(table, vector["chain"])

    def test_round_trip_preserves_non_positional_id(self):
        name = "handoff-field-id-round-trip.json"
        self.assertEqual(errors_of(name), [])
        vector = validator.load_json(validator.ROOT / "vectors/interop-v1" / name)
        vector["expected_output"]["fields"][0]["metadata"]["plenora.field_id"] = "0"
        self.assertTrue(errors_of(name, vector))

    def test_assignment_vector_runs_through_chain_and_gate(self):
        path, vector, _, _ = self.assignment()
        self.assertEqual(interop.vector_errors(path, vector, *gate_inputs(), KERNELS), [])
        self.assertEqual(validator.validate_interop_vectors(validator.load_catalogs()), [])
        vector["chain"][1]["transformations"] = []
        self.assertIn("assigned field id must be a canonical decimal",
                      interop.vector_errors(path, vector, *gate_inputs(), KERNELS))

    def test_assignment_does_not_fix_a_value(self):
        path, vector, table, actual = self.assignment()
        for value in ("0", "17", "982451653"):
            with self.subTest(value=value):
                actual["fields"][0]["metadata"]["plenora.field_id"] = value
                self.assertEqual(interop.output_errors(vector, table, actual), [])
                vector["surface_outputs"] = {"cli": copy.deepcopy(actual), "rust": copy.deepcopy(actual)}
                self.assertEqual(interop.vector_errors(path, vector, *gate_inputs(), KERNELS), [])

    def test_assignment_rejects_divergent_surfaces_without_data(self):
        path, _, table, _ = self.assignment()
        vector = validator.load_json(
            validator.ROOT / "examples/invalid/interop-assignment-vector-divergent-surfaces.json")
        expected = ["surface 1 differs from the first surface at "
                    "/fields/0/metadata/#0 (decision 0022 rule 3)"]
        self.assertEqual(interop.vector_errors(path, vector, *gate_inputs(), KERNELS), expected)
        outputs = vector["surface_outputs"]
        for actual in outputs.values():
            self.assertEqual(interop.output_errors(vector, table, actual), [])
        vector["surface_outputs"] = dict(zip(("SECRET_CLI", "SECRET_RUST"), outputs.values()))
        self.assertEqual(interop.vector_errors(path, vector, *gate_inputs(), KERNELS), expected)

    def test_assignment_requires_multiple_surfaces(self):
        _, vector, table, _ = self.assignment()
        schemas = {name: validator.load_json(validator.ROOT / "schemas" / name)
                   for name in validator.EXPECTED_SCHEMAS}
        registry = validator.schema_registry(schemas)
        schema = schemas["interop-assignment-vector-v1.schema.json"]
        self.assertEqual(validator.instance_errors(schema, vector, registry), [])
        del vector["surface_outputs"]["rust"]
        self.assertTrue(validator.instance_errors(schema, vector, registry))
        self.assertTrue(interop.surface_output_errors(vector, table, vector["surface_outputs"]))
        del vector["surface_outputs"]
        self.assertTrue(validator.instance_errors(schema, vector, registry))

    def test_surface_outputs_are_individually_validated(self):
        path, vector, _, _ = self.assignment()
        vector["surface_outputs"]["rust"]["fields"][0]["metadata"].clear()
        self.assertIn("surface 1: assigned field id must be a canonical decimal",
                      interop.vector_errors(path, vector, *gate_inputs(), KERNELS))
        vector["surface_outputs"]["rust"] = copy.deepcopy(vector["surface_outputs"]["cli"])
        vector["surface_outputs"]["rust"]["rows"][0]["measurement"] = 99
        self.assertTrue(interop.vector_errors(path, vector, *gate_inputs(), KERNELS))

    def test_null_surface_metadata_is_a_clean_rejection(self):
        table = {"schema_metadata": {"plenora.contract.version": "1"},
                 "fields": [{"name": "SECRET_FIELD", "type": "int32",
                             "nullable": False, "metadata": {}}],
                 "rows": [{"SECRET_FIELD": 7}]}
        vector = {"expected_output": table, "assigned_field_ids": [0]}
        actual = copy.deepcopy(table)
        actual["fields"][0]["metadata"] = None
        self.assertEqual(interop.output_errors(vector, table, actual),
                         ["output comparison requires well-formed table fixtures"])

    def test_surface_members_with_unexpected_types_are_rejected_without_data(self):
        _, vector, table, original = self.assignment()
        paths = [("schema_metadata",), ("fields",), ("fields", 0),
                 ("fields", 0, "name"), ("fields", 0, "type"),
                 ("fields", 0, "nullable"), ("fields", 0, "metadata"),
                 ("fields", 0, "metadata", "plenora.field_id"),
                 ("rows",), ("rows", 0), ("rows", 0, "measurement")]
        for path in paths:
            for value in (None, [], {}, True, 17, "SECRET_VALUE"):
                actual = copy.deepcopy(original)
                node = actual
                for key in path[:-1]:
                    node = node[key]
                if type(node[path[-1]]) is type(value):
                    continue
                node[path[-1]] = value
                with self.subTest(path=path, value=value):
                    errors = interop.output_errors(vector, table, actual)
                    self.assertTrue(errors)
                    self.assertNotIn("SECRET", str(errors))

    def test_assignment_rejects_missing_and_noncanonical_ids_without_data(self):
        _, vector, table, actual = self.assignment()
        for value in (None, "", "00", "01", "-1", "+1", "1.0", " 1", "1\n", "١", "SECRET"):
            with self.subTest(value=value):
                metadata = actual["fields"][0]["metadata"]
                if value is None:
                    metadata.pop("plenora.field_id", None)
                else:
                    metadata["plenora.field_id"] = value
                errors = interop.output_errors(vector, table, actual)
                self.assertIn("assigned field id must be a canonical decimal", errors)
                self.assertNotIn("SECRET", str(errors))

    def test_assignment_cannot_mask_replacement_or_change_other_content(self):
        _, vector, table, actual = self.assignment()
        table["fields"][0]["metadata"]["plenora.field_id"] = "123"
        self.assertIn("assigned field must omit its incoming and expected field id",
                      interop.output_errors(vector, table, actual))
        table["fields"][0]["metadata"] = {}
        actual["rows"][0]["measurement"] = 99
        self.assertTrue(interop.output_errors(vector, table, actual))

    def test_assignment_must_be_unique_in_output_schema(self):
        _, vector, table, actual = self.assignment()
        for document in (table, actual, vector["expected_output"]):
            field = copy.deepcopy(document["fields"][0])
            field["name"] = "other"
            field["metadata"] = {"plenora.field_id": "0"}
            document["fields"].append(field)
            document["rows"][0]["other"] = 7
        self.assertIn("the expected output is not a valid table of the vocabulary",
                      interop.output_errors(vector, table, actual))

    def test_assignment_position_is_checked_without_echoing_it(self):
        _, vector, table, actual = self.assignment()
        vector["assigned_field_ids"] = [731731731]
        errors = interop.output_errors(vector, table, actual)
        self.assertIn("assigned field position is outside the table", errors)
        self.assertNotIn("731731731", str(errors))

    def test_mixed_acceptance_and_empty_rejection_have_data_free_messages(self):
        root = validator.ROOT / "vectors/arrow-v1"
        valid = validator.load_json(root / "mixed-without-types.json")
        invalid = validator.load_json(root / "invalid-mixed-empty-types.json")
        self.assertEqual(validator.arrow_semantic_errors(valid), [])
        self.assertEqual(validator.arrow_semantic_errors(invalid),
                         ["field 1 geometry types are empty"])
        verdict = arrow_data.verdict(dict(invalid, rows=[]))
        self.assertEqual((verdict.category, verdict.rule), ("schema", "GEO-016"))
        invalid["fields"][1]["name"] = "SECRET_FIELD"
        invalid["fields"][1]["metadata"]["plenora.geometry.types"] = "SECRET_TYPE"
        self.assertEqual(validator.arrow_semantic_errors(invalid),
                         ["field 1 has an unknown geometry type"])
        for document, category in ((valid, None), (invalid, "schema")):
            document = dict(document, rows=[])
            verdict = arrow_data.verdict(document)
            self.assertEqual(None if verdict is None else verdict.category, category)


if __name__ == "__main__":
    unittest.main()
