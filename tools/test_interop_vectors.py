"""Interoperability vectors (Composition 1.0 section 6, decision 0018): every
expectation is recomputed, every chain checked against the matrix."""

import copy
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

import interop_vectors as interop
import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/interop-v1"


def vector(name):
    return validator.load_json(VECTORS / name)


def errors_of(name, document=None):
    path = VECTORS / name
    catalogs = validator.load_catalogs()
    operations = validator.operation_index(catalogs)
    edges = validator.load_json(ROOT / "composition/pipelines-v1.json")["edges"]
    direct = {
        (
            (edge["from"]["component"], edge["from"]["operation"], edge["from"]["version"]),
            (edge["to"]["component"], edge["to"]["operation"], edge["to"]["version"]),
        )
        for edge in edges if edge["mode"] == "direct"
    }
    return interop.vector_errors(path, document or vector(name), operations, direct, validator.load_json)


class GateTests(unittest.TestCase):
    def test_every_published_vector_passes(self):
        self.assertEqual(validator.validate_interop_vectors(validator.load_catalogs()), [])
        kinds = [vector(path.name)["kind"] for path in VECTORS.glob("*.json")]
        self.assertGreaterEqual(kinds.count("handoff"), 7)
        self.assertGreaterEqual(kinds.count("rejection"), 23)
        self.assertGreaterEqual(kinds.count("source"), 1)

    def test_the_gate_reports_an_empty_directory(self):
        catalogs = validator.load_catalogs()
        original = validator.ROOT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "composition").mkdir()
            shutil.copy(original / "composition/pipelines-v1.json", root / "composition/pipelines-v1.json")
            try:
                validator.ROOT = root
                errors = validator.validate_interop_vectors(catalogs)
            finally:
                validator.ROOT = original
        self.assertEqual(errors, ["vectors/interop-v1 has no vectors"])


class HandoffTests(unittest.TestCase):
    def test_an_undeclared_change_is_reported(self):
        document = vector("handoff-io-data-io-points.json")
        document["expected_output"]["fields"][1]["metadata"]["plenora.geometry.axis_order"] = "lat_lon"
        self.assertIn("expected_output differs", errors_of("handoff-io-data-io-points.json", document)[0])

    def test_a_missing_transformation_is_reported(self):
        document = vector("handoff-io-database-io.json")
        document["chain"][2]["transformations"].remove("axis_order_unknown")
        self.assertTrue(any("differs" in error for error in errors_of("handoff-io-database-io.json", document)))

    def test_a_chain_outside_the_matrix_is_reported(self):
        document = vector("handoff-io-data-io-points.json")
        document["chain"].reverse()
        errors = errors_of("handoff-io-data-io-points.json", document)
        self.assertTrue(any("not a direct edge" in error for error in errors))

    def test_a_target_round_trip_needs_write_then_read(self):
        document = vector("handoff-io-database-io.json")
        document["chain"][1]["operation"] = "database.query"
        errors = errors_of("handoff-io-database-io.json", document)
        self.assertTrue(any("not a write then a read" in error for error in errors))
        first = vector("handoff-database-data-io.json")
        first["chain"][0]["via"] = "target"
        self.assertTrue(any("first step" in error for error in errors_of("handoff-database-data-io.json", first)))

    def test_unknown_operation_and_reserved_prefix(self):
        document = vector("handoff-io-database-io.json")
        document["chain"][2]["provider_prefix"] = "plenora.geometry."
        document["chain"][0]["version"] = 9
        errors = errors_of("handoff-io-database-io.json", document)
        self.assertTrue(any("reserved" in error for error in errors))
        self.assertTrue(any("unknown operation" in error for error in errors))

    def test_input_must_exist_and_be_valid(self):
        document = vector("handoff-io-data-io-points.json")
        document["input"] = "../arrow-data-v1/absent.json"
        self.assertIn("does not exist", errors_of("handoff-io-data-io-points.json", document)[0])
        document["input"] = "../arrow-data-v1/invalid-wkb-truncated.json"
        self.assertIn("valid input", errors_of("handoff-io-data-io-points.json", document)[0])

    def test_transformations(self):
        table = {
            "schema_metadata": {"plenora.contract.version": "1"},
            "fields": [
                {"name": "a", "type": "large_utf8", "nullable": True, "metadata": {}},
                {"name": "b", "type": "int64", "nullable": True, "metadata": {"plenora.field_id": "0"}},
            ],
            "rows": [{"a": "x", "b": 1}],
        }
        interop.large_to_standard(table)
        interop.assign_field_ids(table)
        self.assertEqual(table["fields"][0]["type"], "utf8")
        self.assertEqual(table["fields"][0]["metadata"]["plenora.field_id"], "1")
        value = struct.pack("<BIi", 1, 1 | 0x20000000, 3003) + bytes(16)
        with self.assertRaises(ValueError):
            interop._with_srid(value, 4326)
        self.assertEqual(interop._with_srid(value, 3003), value)
        big = struct.pack(">BI", 0, 1) + bytes(16)
        self.assertEqual(interop._with_srid(big, 4326)[1:5], struct.pack(">I", 1 | 0x20000000))

    def test_an_input_that_is_not_a_table(self):
        for name in ("handoff-io-data-io-points.json", "rejection-wkb-truncated-data-run.json"):
            document = vector(name)
            path = (VECTORS / document["input"]).resolve()
            broken = validator.load_json(path)
            broken["rows"][0]["id"] = None
            catalogs = validator.load_catalogs()
            errors = interop.vector_errors(
                VECTORS / name, document, validator.operation_index(catalogs), set(),
                lambda _path, broken=broken: broken,
            )
            with self.subTest(name):
                self.assertTrue(any("not a buildable table" in error for error in errors))

    def test_a_transformation_that_cannot_apply(self):
        document = vector("handoff-io-data-io-ewkb.json")
        document["input"] = "../arrow-data-v1/invalid-ewkb-srid-differs.json"
        self.assertTrue(errors_of("handoff-io-data-io-ewkb.json", document))


class RejectionTests(unittest.TestCase):
    def test_input_class_must_match_the_input_vector(self):
        name = "rejection-ewkb-srid-differs-database-write.json"
        document = vector(name)
        document["expected_error"]["category"] = "resource_limit"
        document["expected_error"]["rules"] = ["ARROW-013"]
        document["expected_error"]["class"] = "support"
        document["expected_error"]["phases"] = ["write"]
        self.assertEqual(len(errors_of(name, document)), 4)

    def test_a_valid_input_needs_a_class_and_its_rule(self):
        name = "rejection-two-geometries-io-write.json"
        document = vector(name)
        document["expected_error"]["class"] = "input"
        self.assertEqual(errors_of(name, document), ["a valid input cannot be rejected as class input"])
        document = vector(name)
        document["expected_error"]["rules"] = ["ARROW-013"]
        document["expected_error"]["category"] = "schema"
        self.assertEqual(len(errors_of(name, document)), 2)

    def test_crs_rejections_need_their_reason(self):
        name = "rejection-lat-lon-geo-operation.json"
        document = vector(name)
        document["input"] = "../arrow-data-v1/axis-lon-lat-epsg4326.json"
        self.assertEqual(len(errors_of(name, document)), 1)
        document = vector("rejection-unknown-crs-geo-operation.json")
        document["expected_error"]["rules"] = ["ARROW-013"]
        self.assertEqual(len(errors_of("rejection-unknown-crs-geo-operation.json", document)), 1)

    def test_data_mapping_admits_read_and_write(self):
        document = vector("rejection-wkb-truncated-data-run.json")
        self.assertEqual(document["expected_error"]["phases"], ["read", "write"])


class SourceTests(unittest.TestCase):
    def test_coordinates_are_read_from_the_document(self):
        name = "source-geojson-points.json"
        document = vector(name)
        document["expected_geometry"]["coordinates"][0].reverse()
        document["expected_geometry"]["axis_order"] = "lat_lon"
        document["expected_geometry"]["crs_id"] = "EPSG:4326"
        self.assertEqual(len(errors_of(name, document)), 3)

    def test_a_source_must_be_able_to_show_an_exchange(self):
        name = "source-geojson-points.json"
        document = vector(name)
        text = json.loads(document["source"]["text"])
        text["features"] = text["features"][1:]
        document["source"]["text"] = json.dumps(text)
        document["expected_geometry"]["coordinates"] = [[12.4964, 41.9028]]
        self.assertTrue(any("VOC-003" in error for error in errors_of(name, document)))

    def test_unreadable_sources_and_wrong_steps(self):
        name = "source-geojson-points.json"
        for text in ('{"type":"Feature"}', '{"type":"FeatureCollection","features":[{"geometry":{"type":"LineString","coordinates":[]}}]}'):
            document = vector(name)
            document["source"]["text"] = text
            with self.subTest(text):
                self.assertTrue(any("not readable" in error for error in errors_of(name, document)))
        document = vector(name)
        document["chain"][0]["transformations"] = ["assign_field_ids"]
        self.assertEqual(len(errors_of(name, copy.deepcopy(document))), 1)


if __name__ == "__main__":
    unittest.main()
