"""Interoperability vectors (Composition 1.0 section 6, decision 0018): one
ordered evaluation per step, expectations recomputed, chains checked against
the matrix, messages without values."""

import copy
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

import arrow_data
import interop_vectors as interop
import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/interop-v1"
KERNELS = {kernel["id"] for kernel in validator.load_json(ROOT / "catalogs/data-kernels-v2.json")["operations"]}


def vector(name):
    return validator.load_json(VECTORS / name)


def errors_of(name, document=None, load=validator.load_json):
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
    return interop.vector_errors(VECTORS / name, document or vector(name), operations, direct, load, KERNELS)


def step(operation, component, version=2, **params):
    return {"component": component, "operation": operation, "version": version,
            "params": params, "transformations": []}


GEO_STEP = step("data.run", "plenora-data-tools", plan="geo.centroid")
IDENTITY = step("data.run", "plenora-data-tools", plan="identity")
IO_READ = step("io.read", "plenora-io-tools")
IO_WRITE_IPC = step("io.write", "plenora-io-tools", format="arrow_ipc_file")
IO_WRITE_GPKG = step("io.write", "plenora-io-tools", format="gpkg")
DB_WRITE = step("database.write", "plenora-database-tools", version=1)


def table(name):
    return validator.load_json(ROOT / "vectors/arrow-data-v1" / name)


class GateTests(unittest.TestCase):
    def test_every_published_vector_passes(self):
        self.assertEqual(validator.validate_interop_vectors(validator.load_catalogs()), [])
        kinds = [vector(path.name)["kind"] for path in VECTORS.glob("*.json")]
        self.assertGreaterEqual(kinds.count("handoff"), 9)
        self.assertGreaterEqual(kinds.count("rejection"), 26)
        self.assertGreaterEqual(kinds.count("source"), 2)

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


class OrderTests(unittest.TestCase):
    """REJ-002 with the operation: one evaluation, one answer."""

    def test_unknown_crs_before_values_for_a_computing_step(self):
        found = interop.step_rejection(table("invalid-unknown-crs-and-truncated.json"), GEO_STEP, KERNELS)
        self.assertEqual(found, interop.Rejection("crs", "crs", "GEO-015"))
        self.assertEqual(interop.step_rejection(table("invalid-unknown-crs-and-truncated.json"), DB_WRITE, KERNELS),
                         interop.Rejection("input", "data_mapping", "GEO-011"))
        self.assertIsNone(interop.step_rejection(table("invalid-unknown-crs-and-truncated.json"), IO_READ, KERNELS))

    def test_support_before_values(self):
        limited = step("io.write", "plenora-io-tools", format="gpkg", limits=["one_geometry_field"])
        self.assertEqual(interop.step_rejection(table("invalid-two-geometries-and-truncated.json"), limited, KERNELS),
                         interop.Rejection("support", "unsupported", "GEO-012"))
        types = step("io.write", "plenora-io-tools", format="gpkg", limits=["one_geometry_type"])
        self.assertEqual(interop.step_rejection(table("types-point-polygon.json"), types, KERNELS),
                         interop.Rejection("support", "unsupported", "GEO-010"))

    def test_steps_that_carry_do_not_decode(self):
        for carrier in (IO_READ, IDENTITY, IO_WRITE_IPC):
            with self.subTest(carrier["operation"]):
                self.assertIsNone(interop.step_rejection(table("invalid-ewkb-srid-differs.json"), carrier, KERNELS))
        self.assertIsNotNone(interop.step_rejection(table("invalid-ewkb-srid-differs.json"), IO_WRITE_GPKG, KERNELS))

    def test_a_computing_step_needs_a_registered_geo_kernel(self):
        for plan in ("identity", "geo.unknown_kernel"):
            with self.subTest(plan):
                self.assertIsNone(interop.step_rejection(
                    table("crs-unknown-identifier.json"), step("data.run", "plenora-data-tools", plan=plan), KERNELS))
        self.assertEqual(interop.step_rejection(table("axis-lat-lon-stored.json"), GEO_STEP, KERNELS).rule,
                         "DT-ARROW-004")
        field = copy.deepcopy(table("crs-id-with-consistent-definition.json"))
        del field["fields"][1]["metadata"]["plenora.geometry.crs_id"]
        self.assertEqual(interop.step_rejection(field, GEO_STEP, KERNELS).rule, "GEO-006")

    def test_version_before_the_profile_acceptance(self):
        broken = copy.deepcopy(table("axis-lon-lat-epsg4326.json"))
        broken["schema_metadata"]["plenora.contract.version"] = "2"
        broken["fields"][0]["metadata"]["plenora.field_id"] = "x"
        self.assertEqual(interop.step_rejection(broken, IDENTITY, KERNELS),
                         interop.Rejection("input", "unsupported", "ARROW-002"))

    def test_geography_and_edges_for_a_computing_step(self):
        self.assertEqual(interop.step_rejection(table("geography-point.json"), GEO_STEP, KERNELS),
                         interop.Rejection("support", "unsupported", "DT-ARROW-004"))
        self.assertEqual(interop.step_rejection(table("invalid-geography-and-truncated.json"), GEO_STEP, KERNELS),
                         interop.Rejection("support", "unsupported", "DT-ARROW-004"))
        self.assertIsNone(interop.step_rejection(table("geography-point.json"), IDENTITY, KERNELS))
        spherical = copy.deepcopy(table("axis-lon-lat-epsg4326.json"))
        spherical["fields"][1]["metadata"]["ARROW:extension:metadata"] = '{"edges":"spherical"}'
        self.assertEqual(interop.step_rejection(spherical, GEO_STEP, KERNELS).rule, "DT-ARROW-004")
        spherical["fields"][1]["metadata"]["ARROW:extension:metadata"] = "{"
        self.assertEqual(interop._edges(spherical["fields"][1]), "unreadable")

    def test_the_profile_acceptance_of_data_run(self):
        self.assertIsNone(interop.step_rejection(table("invalid-axis-order-missing.json"), IDENTITY, KERNELS))
        incomplete = table("invalid-precision-missing.json")
        self.assertIsNone(interop.step_rejection(incomplete, IDENTITY, KERNELS))
        self.assertEqual(interop.step_rejection(incomplete, IO_READ, KERNELS).category, "schema")
        bare = copy.deepcopy(table("axis-lon-lat-epsg4326.json"))
        for key in ("crs_resolution", "axis_order", "encoding"):
            del bare["fields"][1]["metadata"][f"plenora.geometry.{key}"]
        interop.complete_missing_geometry_keys(bare)
        self.assertEqual(bare["fields"][1]["metadata"]["plenora.geometry.crs_resolution"], "declared_unresolved")


class HandoffTests(unittest.TestCase):
    def test_an_undeclared_change_names_only_the_path(self):
        document = vector("handoff-io-data-io-points.json")
        document["expected_output"]["fields"][1]["metadata"]["plenora.geometry.axis_order"] = "lat_lon"
        errors = errors_of("handoff-io-data-io-points.json", document)
        self.assertEqual(errors, ["expected_output differs from the recomputed table at /fields/1/metadata/#2"])

    def test_a_missing_transformation_is_reported(self):
        document = vector("handoff-io-database-io.json")
        document["chain"][2]["transformations"].remove("axis_order_unknown")
        self.assertTrue(any("differs" in error for error in errors_of("handoff-io-database-io.json", document)))

    def test_a_step_that_rejects_its_input(self):
        document = vector("handoff-data-io-profile-completion.json")
        document["chain"][0]["transformations"].remove("complete_missing_geometry_keys")
        self.assertIn("step 2 rejects its input", errors_of("handoff-data-io-profile-completion.json", document)[0])

    def test_delegated_metadata_is_explicit(self):
        document = vector("handoff-io-database-io.json")
        self.assertEqual(document["expected_output"]["delegated_metadata"], ["plenora.postgres."])
        del document["expected_output"]["delegated_metadata"]
        self.assertTrue(any("delegated_metadata" in error for error in errors_of("handoff-io-database-io.json", document)))

    def test_iso_codes_become_extended_before_the_srid(self):
        value = struct.pack("<BI", 1, 1001) + struct.pack("<ddd", 1, 2, 3)
        converted = interop.with_srid(value, 4326)
        self.assertEqual(struct.unpack("<I", converted[1:5])[0], 1 | arrow_data.FLAG_Z | arrow_data.FLAG_SRID)
        self.assertEqual(arrow_data.decode_wkb(converted), arrow_data.Geometry("point", "xyz", 4326))
        xym = struct.pack("<BI", 1, 2001) + struct.pack("<ddd", 1, 2, 3)
        self.assertEqual(struct.unpack("<I", interop.with_srid(xym, 7)[1:5])[0], 0x60000001)
        self.assertEqual(arrow_data.decode_wkb(interop.with_srid(xym, 7)).dimensions, "xym")
        zm = struct.pack(">BI", 0, 3001) + struct.pack(">dddd", 1, 2, 3, 4)
        self.assertEqual(arrow_data.decode_wkb(interop.with_srid(zm, 1)).dimensions, "xyzm")
        present = struct.pack("<BIi", 1, 1 | arrow_data.FLAG_SRID, 3003) + bytes(16)
        self.assertEqual(interop.with_srid(present, 3003), present)
        with self.assertRaises(ValueError):
            interop.with_srid(present, 4326)

    def test_chain_rules(self):
        document = vector("handoff-io-data-io-points.json")
        document["chain"].reverse()
        self.assertTrue(any("not a direct edge" in error for error in errors_of("handoff-io-data-io-points.json", document)))
        document = vector("handoff-io-database-io.json")
        document["chain"][1]["operation"] = "database.query"
        self.assertTrue(any("write then a read" in error for error in errors_of("handoff-io-database-io.json", document)))
        first = vector("handoff-database-data-io.json")
        first["chain"][0]["via"] = "target"
        self.assertTrue(any("first step" in error for error in errors_of("handoff-database-data-io.json", first)))
        odd = vector("handoff-io-database-io.json")
        odd["chain"][2]["provider_prefix"] = "plenora.geometry."
        odd["chain"][0]["version"] = 9
        odd["chain"][0]["params"]["limits"] = ["nothing"]
        odd["chain"][0]["transformations"] = ["srid_from_epsg_identifier"]
        errors = errors_of("handoff-io-database-io.json", odd)
        for text in ("reserved", "unknown operation", "unknown limit", "cannot declare"):
            self.assertTrue(any(text in error for error in errors), text)

    def test_order_of_transformations_and_types(self):
        forward = [{"transformations": ["srid_from_epsg_identifier", "ewkb_with_field_srid"]}]
        backward = [{"transformations": ["ewkb_with_field_srid", "srid_from_epsg_identifier"]}]
        start = table("axis-lon-lat-epsg4326.json")
        self.assertEqual(interop.expected_output(start, forward), interop.expected_output(start, backward))
        self.assertFalse(interop.same(1, 1.0))
        self.assertEqual(interop.difference({"a": [1, 2]}, {"a": [1]}), "/#0 (length)")
        self.assertEqual(interop.difference({"a": 1}, {"b": 1}), "/#0")
        self.assertEqual(interop.difference({"rows": [{"segreto": 1}]}, {"rows": [{"segreto": 2}]}), "/rows/0/#0")
        self.assertEqual(interop.difference(1, True), "/")
        self.assertIsNone(interop.difference({"a": [1]}, {"a": [1]}))
        wide = {"schema_metadata": {}, "rows": [{"a": "x"}],
                "fields": [{"name": "a", "type": "large_utf8", "nullable": True, "metadata": {}}]}
        interop.large_to_standard(wide)
        interop.assign_field_ids(wide)
        self.assertEqual((wide["fields"][0]["type"], wide["fields"][0]["metadata"]["plenora.field_id"]), ("utf8", "0"))

    def test_inputs_that_do_not_exist_or_are_not_tables(self):
        document = vector("handoff-io-data-io-points.json")
        document["input"] = "../arrow-data-v1/absent.json"
        self.assertIn("does not exist", errors_of("handoff-io-data-io-points.json", document)[0])
        for name in ("handoff-io-data-io-points.json", "rejection-wkb-truncated-database-write.json"):
            source = vector(name)
            broken = validator.load_json((VECTORS / source["input"]).resolve())
            broken["rows"][0]["id"] = None
            with self.subTest(name):
                self.assertIn("not a buildable table", errors_of(name, source, lambda _path, b=broken: b)[0])
        bad = vector("handoff-io-data-io-ewkb.json")
        bad["input"] = "../arrow-data-v1/invalid-ewkb-srid-differs.json"
        self.assertTrue(errors_of("handoff-io-data-io-ewkb.json", bad))


class RejectionTests(unittest.TestCase):
    def test_class_category_rule_and_axes(self):
        name = "rejection-ewkb-srid-differs-database-write.json"
        document = vector(name)
        document["expected_error"].update(category="resource_limit", rules=["REJ-001"], phases=["validate"],
                                          remote_effects=["none"])
        document["expected_error"]["class"] = "support"
        self.assertEqual(len(errors_of(name, document)), 5)
        reader = vector("rejection-wkb-truncated-data-run-geo.json")
        self.assertEqual((reader["expected_error"]["phases"], reader["expected_error"]["remote_effects"]),
                         (["read"], ["none"]))

    def test_an_accepted_input_is_not_a_rejection(self):
        name = "rejection-unknown-crs-geo-operation.json"
        document = vector(name)
        document["chain"][0]["params"]["plan"] = "identity"
        self.assertEqual(errors_of(name, document), ["the step accepts the input under REJ-002"])

    def test_published_order_vectors(self):
        self.assertEqual(vector("rejection-unknown-crs-and-truncated-geo.json")["expected_error"]["category"], "crs")
        self.assertEqual(
            vector("rejection-two-geometries-and-truncated-io-write.json")["expected_error"]["category"],
            "unsupported",
        )


class SourceTests(unittest.TestCase):
    def test_geojson(self):
        name = "source-geojson-points.json"
        document = vector(name)
        document["expected_geometry"]["coordinates"][0].reverse()
        document["expected_geometry"]["axis_order"] = "lat_lon"
        document["expected_geometry"]["crs_id"] = "EPSG:4326"
        self.assertEqual(len(errors_of(name, document)), 3)
        narrow = vector(name)
        text = json.loads(narrow["source"]["text"])
        text["features"] = text["features"][1:]
        narrow["source"]["text"] = json.dumps(text)
        narrow["expected_geometry"]["coordinates"] = [[12.4964, 41.9028]]
        self.assertTrue(any("GEO-003" in error for error in errors_of(name, narrow)))
        for broken in ('{"type":"Feature"}',
                       '{"type":"FeatureCollection","features":[{"geometry":{"type":"LineString","coordinates":[]}}]}'):
            unreadable = vector(name)
            unreadable["source"]["text"] = broken
            self.assertEqual(errors_of(name, unreadable)[-1], "source is not readable")
        transformed = vector(name)
        transformed["chain"][0]["transformations"] = ["assign_field_ids"]
        self.assertEqual(len(errors_of(name, transformed)), 1)

    def test_wkt_csv(self):
        name = "source-wkt-csv-utm.json"
        self.assertEqual(errors_of(name), [])
        request = vector(name)
        request["chain"][0]["params"]["axis_order"] = "northing_easting"
        self.assertTrue(any("read request" in error for error in errors_of(name, request)))
        geographic = vector(name)
        geographic["expected_geometry"]["crs_id"] = "EPSG:4326"
        geographic["chain"][0]["params"]["crs_id"] = "EPSG:4326"
        self.assertTrue(any("UTM" in error for error in errors_of(name, geographic)))
        low = vector(name)
        low["source"]["text"] = "id,wkt\n1,POINT (500000 400000)\n"
        low["expected_geometry"]["coordinates"] = [[500000, 400000]]
        self.assertTrue(any("GEO-003" in error for error in errors_of(name, low)))
        bad = vector(name)
        bad["source"]["text"] = "id,wkt\n1,LINESTRING (0 0, 1 1)\n"
        self.assertEqual(errors_of(name, bad), ["source is not readable"])


if __name__ == "__main__":
    unittest.main()
