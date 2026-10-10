"""Arrow Vocabulary 1.0 sections 7-12 (decision 0013): the verdicts the
validator derives for the data vectors, and the decoders behind them."""

import copy
import json
import struct
import unittest
from decimal import Decimal

import arrow_data as data
import validate_specs as validator

ROOT = validator.ROOT
VECTORS = ROOT / "vectors/arrow-data-v1"


def vector(name):
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


def point(x=-120.5, y=45.25, srid=None, code=1, order=1):
    prefix = "<" if order == 1 else ">"
    if srid is not None:
        code |= data.FLAG_SRID
    head = struct.pack(prefix + "BI", order, code)
    if srid is not None:
        head += struct.pack(prefix + "i", srid)
    return head + struct.pack(prefix + "dd", x, y)


def collection(code, members):
    return struct.pack("<BII", 1, code, len(members)) + b"".join(members)


class WkbTests(unittest.TestCase):
    def test_point_in_both_byte_orders(self):
        self.assertEqual(data.decode_wkb(point()), data.Geometry("point", "xy", None))
        self.assertEqual(data.decode_wkb(point(order=0)), data.Geometry("point", "xy", None))

    def test_iso_and_extended_dimensions(self):
        xyzm = struct.pack("<BI", 1, 3001) + struct.pack("<dddd", 1, 2, 3, 4)
        self.assertEqual(data.decode_wkb(xyzm).dimensions, "xyzm")
        xym = struct.pack("<BI", 1, 1 | data.FLAG_M) + struct.pack("<ddd", 1, 2, 3)
        self.assertEqual(data.decode_wkb(xym).dimensions, "xym")

    def test_srid_is_read_on_the_outer_geometry(self):
        self.assertEqual(data.decode_wkb(point(srid=4326)).srid, 4326)

    def test_containers_and_their_members(self):
        ring = struct.pack("<I", 4) + struct.pack("<8d", 0, 0, 1, 0, 1, 1, 0, 0)
        polygon = struct.pack("<BII", 1, 3, 1) + ring
        self.assertEqual(data.decode_wkb(collection(6, [polygon])).type, "multipolygon")
        self.assertEqual(data.decode_wkb(collection(7, [point(), polygon])).type, "geometrycollection")
        line = struct.pack("<BII", 1, 2, 2) + struct.pack("<4d", 0, 0, 1, 1)
        self.assertEqual(data.decode_wkb(collection(9, [line])).type, "compoundcurve")

    def test_malformed_values(self):
        cases = {
            "empty": b"",
            "byte order": b"\x02" + point()[1:],
            "unknown type": struct.pack("<BI", 1, 13),
            "unknown thousands": struct.pack("<BI", 1, 4001),
            "iso and extended flags": struct.pack("<BI", 1, 1001 | data.FLAG_Z) + bytes(24),
            "truncated": point()[:-1],
            "trailing bytes": point() + b"\x00",
            "member type": collection(4, [struct.pack("<BII", 1, 2, 0)]),
            "member dimensions": collection(4, [struct.pack("<BI", 1, 1001) + bytes(24)]),
            "member srid": collection(4, [point(srid=4326)]),
            "too many members": struct.pack("<BII", 1, 4, 1000),
            "too many rings": struct.pack("<BII", 1, 3, 1000),
            "too many points": struct.pack("<BII", 1, 2, 1000),
            "linestring of one point": struct.pack("<BII", 1, 2, 1) + bytes(16),
            "open ring": struct.pack("<BIII", 1, 3, 1, 4) + struct.pack("<8d", 0, 0, 1, 0, 1, 1, 0, 1),
            "short ring": struct.pack("<BIII", 1, 3, 1, 3) + struct.pack("<6d", 0, 0, 1, 0, 0, 0),
            "triangle with two rings": struct.pack("<BII", 1, 17, 2),
            "even circular string": struct.pack("<BII", 1, 8, 2) + bytes(32),
            "iso code with srid flag": struct.pack("<BIi", 1, 1001 | data.FLAG_SRID, 4326) + bytes(24),
        }
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(data.Malformed):
                data.decode_wkb(value)

    def test_nesting_is_bounded(self):
        value = point()
        for _ in range(data.MAX_DEPTH + 1):
            value = collection(7, [value])
        with self.assertRaises(data.Malformed):
            data.decode_wkb(value)


class DefinitionTests(unittest.TestCase):
    def test_top_level_identifiers_only(self):
        text = 'PROJCS["x",GEOGCS["y",AUTHORITY["EPSG","4326"]],AUTHORITY["EPSG","3003"]]'
        self.assertEqual(data.definition_identifiers(text, "wkt"), [("EPSG", "3003")])
        self.assertTrue(data.definition_contradicts("EPSG:4326", text, "wkt"))
        self.assertFalse(data.definition_contradicts("EPSG:3003", text, "wkt"))

    def test_numeric_codes_and_case_insensitive_authority(self):
        text = 'GEOGCRS["x",ID["epsg",4326],ID["OGC","CRS84"]]'
        self.assertEqual(data.definition_identifiers(text, "wkt2"), [("epsg", "4326"), ("OGC", "CRS84")])
        self.assertFalse(data.definition_contradicts("EPSG:4326", text, "wkt2"))
        self.assertFalse(data.definition_contradicts("OGC:CRS84", text, "wkt2"))

    def test_other_authority_and_identifier_without_colon_are_not_compared(self):
        text = 'GEOGCRS["x",ID["ESRI",104000]]'
        self.assertFalse(data.definition_contradicts("EPSG:4326", text, "wkt2"))
        self.assertFalse(data.definition_contradicts("LOCAL", 'GEOGCRS["x",ID["EPSG",1]]', "wkt2"))

    def test_projjson_identifiers(self):
        self.assertEqual(
            data.definition_identifiers('{"ids":[{"authority":"EPSG","code":"4326"}]}', "projjson"),
            [("EPSG", "4326")],
        )
        self.assertEqual(data.definition_identifiers('{"type":"GeographicCRS"}', "projjson"), [])

    def test_malformed_definitions(self):
        cases = [
            ('GEOGCRS["x"', "wkt2"),
            ('GEOGCRS["x"] extra', "wkt2"),
            ('GEOGCRS["x";1]', "wkt2"),
            ('"x"', "wkt2"),
            ('GEOGCRS[]', "wkt2"),
            ('GEOGCRS["x",ID[4326]]', "wkt2"),
            ('GEOGCRS["x",ID["EPSG",FOO]]', "wkt2"),
            ('GEOGCRS["x",ID["EPSG",43.26]]', "wkt2"),
            ('GEOGCRS["x",ID["EPSG",4326)]', "wkt2"),
            ('GEOGCS["x",AUTHORITY["EPSG","4327"]]', "wkt2"),
            ('GEOGCRS["x",ID["EPSG",4326]]', "wkt"),
            ('GEOGCRS["x",ID["EPSG",٤٣٢٦]]', "wkt2"),
            ('GEOGCRS["x" #]', "wkt2"),
            ("[]", "projjson"),
            ("{", "projjson"),
            ('{"a":1,"a":2}', "projjson"),
            ('{"x":NaN}', "projjson"),
            ('{"id":{},"ids":[]}', "projjson"),
            ('{"ids":{}}', "projjson"),
            ('{"id":{"authority":"EPSG","code":true}}', "projjson"),
        ]
        for text, kind in cases:
            with self.subTest(text), self.assertRaises(data.Malformed):
                data.definition_identifiers(text, kind)

    def test_wkt_nesting_is_bounded(self):
        text = "A[" * (data.MAX_DEPTH + 2) + "1" + "]" * (data.MAX_DEPTH + 2)
        with self.assertRaises(data.Malformed):
            data.parse_wkt(text)

    def test_parts_of_the_three_formats(self):
        wkt2 = (
            'PROJCRS["x",BASEGEOGCRS["y",DATUM["d",ELLIPSOID["e",6378137,298.257223563]],ID["EPSG",4326]],'
            'CONVERSION["c",METHOD["Transverse Mercator"],PARAMETER["False easting",500000,'
            'LENGTHUNIT["metre",1]]],ID["EPSG",32632]]'
        )
        parts = data.definition_parts(wkt2, "wkt2")
        self.assertEqual(parts.conversion, ("transverse_mercator", {"false_easting": Decimal("500000")}))
        self.assertTrue(parts.units_decided and parts.prime_meridian_zero)
        self.assertEqual(parts.kind, "projected")
        self.assertEqual(parts.bases, [("EPSG", "4326")])
        self.assertEqual(parts.ellipsoid, data.WGS84)
        self.assertTrue(data.definition_parts('BOUNDCRS[SOURCECRS[GEOGCRS["x"]]]', "wkt2").datum_shift)
        projjson = data.definition_parts(
            '{"type":"GeographicCRS","datum_ensemble":{"ellipsoid":'
            '{"semi_major_axis":6378137,"inverse_flattening":298.257223563}},'
            '"prime_meridian":{"longitude":0}}',
            "projjson",
        )
        self.assertEqual(projjson.ellipsoid, (Decimal("6378137"), Decimal("298.257223563")))
        self.assertTrue(projjson.prime_meridian_zero)
        self.assertEqual(data.definition_parts('{"type":"BoundCRS"}', "projjson").kind, "other")
        undecidable = [
            ('{"type":"ProjectedCRS"}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},"conversion":{"method":{"name":"Lambert"},"parameters":[]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},"conversion":{"method":{"name":"Transverse Mercator"},'
             '"parameters":[{"name":"Azimuth","value":1}]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},"conversion":{"method":{"name":"Transverse Mercator"},'
             '"parameters":[1]}}', "projjson"),
            ('{"type":"GeographicCRS","datum":{"ellipsoid":{"semi_major_axis":{"value":1},"inverse_flattening":1}}}',
             "projjson"),
            ('GEOGCS["x",DATUM["d",SPHEROID["e",6378137]]]', "wkt"),
            ('GEOGCS["x",DATUM["d",SPHEROID["e","a","b"]]]', "wkt"),
            ('GEOGCS["x",UNIT[1]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"],PROJECTION["Lambert"]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"]]', "wkt"),
            ('PROJCS["x",PROJECTION["Transverse_Mercator"]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"],PROJECTION["Transverse_Mercator"],PARAMETER["k"]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"],PROJECTION["Transverse_Mercator"],PARAMETER["scale_factor",1],'
             'PARAMETER["scale_factor",1]]', "wkt"),
        ]
        for text, kind in undecidable:
            with self.subTest(text), self.assertRaises(data.Undecidable):
                data.definition_parts(text, kind)
        units = data.definition_parts(
            '{"type":"ProjectedCRS","base_crs":{},"conversion":{"method":{"name":"Transverse Mercator"},'
            '"parameters":[{"name":"False easting","value":1,"unit":{"name":"foot","conversion_factor":0.3048}}]}}',
            "projjson",
        )
        self.assertFalse(units.units_decided)
        with self.assertRaises(data.Undecidable):
            data.definition_parts(
                '{"type":"ProjectedCRS","base_crs":{},"conversion":{"method":{"name":"Transverse Mercator"},'
                '"parameters":[{"name":"False easting","value":1,"unit":3}]}}', "projjson")


def geometry_field(**metadata):
    base = {
        "plenora.field_id": "1",
        "ARROW:extension:name": "geoarrow.wkb",
        "plenora.geometry.encoding": "wkb",
        "plenora.geometry.dimensions": "xy",
        "plenora.geometry.spatial_semantics": "geometry",
        "plenora.geometry.precision": "float64",
        "plenora.geometry.types_declaration": "exact",
        "plenora.geometry.types": "point",
        "plenora.geometry.crs_resolution": "resolved",
        "plenora.geometry.crs_id": "EPSG:4326",
        "plenora.geometry.axis_order": "lon_lat",
    }
    for key, value in metadata.items():
        name = key if key.startswith(("plenora.", "ARROW:")) else f"plenora.geometry.{key}"
        if value is None:
            base.pop(name, None)
        else:
            base[name] = value
    return {"name": "geometry", "type": "binary", "nullable": True, "metadata": base}


def table(field, value=None, version="1"):
    metadata = {} if version is None else {"plenora.contract.version": version}
    return {
        "schema_metadata": metadata,
        "fields": [field],
        "rows": [{"geometry": (value if value is not None else point()).hex()}],
    }


class VerdictTests(unittest.TestCase):
    def assertVerdict(self, document, category, rule):
        self.assertEqual(data.verdict(document), data.Verdict(category, rule))

    def test_contract_version(self):
        self.assertVerdict(table(geometry_field(), version=None), "schema", "ARROW-001")
        self.assertVerdict(table(geometry_field(), version="01"), "schema", "ARROW-001")
        self.assertVerdict(table(geometry_field(), version="1\n"), "schema", "ARROW-001")
        native = geometry_field(**{"plenora.geometry.native.grid": "1"})
        self.assertIsNone(data.verdict(table(native)))
        self.assertVerdict(table(geometry_field(), version="2"), "unsupported", "ARROW-002")

    def test_vocabulary_well_formedness(self):
        cases = [
            {"plenora.field_id": "-1"},
            {"encoding": "twkb"},
            {"precision": None},
            {"srid": "4326.0"},
            {"srid": str(2**31)},
            {"types_declaration": "unresolved"},
            {"types": "hexagon"},
            {"crs_id": ""},
            {"crs_id": "4326"},
            {"plenora.field_id": "1\n"},
            {"srid": "4326\n"},
            {"types": ""},
            {"plenora.geometry.sird": "4326"},
        ]
        for metadata in cases:
            with self.subTest(metadata):
                self.assertVerdict(table(geometry_field(**metadata)), "schema", data.VOCABULARY)
        plain = {"name": "geometry", "type": "binary", "nullable": True,
                 "metadata": {"plenora.geometry.encoding": "wkb"}}
        self.assertVerdict(table(plain), "schema", data.VOCABULARY)
        utf8 = geometry_field()
        utf8["type"] = "utf8"
        document = table(utf8)
        document["rows"] = [{"geometry": "x"}]
        self.assertVerdict(document, "schema", data.VOCABULARY)
        twice = table(geometry_field())
        twice["fields"].append({"name": "id", "type": "int64", "nullable": True,
                                "metadata": {"plenora.field_id": "1"}})
        twice["rows"][0]["id"] = 1
        self.assertVerdict(twice, "schema", data.VOCABULARY)

    def test_crs_state(self):
        cases = [
            {"crs_definition": "GEOGCRS[\"x\"]"},
            {"crs_resolution": "missing"},
            {"crs_id": None},
        ]
        for metadata in cases:
            with self.subTest(metadata):
                self.assertVerdict(table(geometry_field(**metadata)), "crs", data.VOCABULARY)
        only_definition = geometry_field(crs_id=None, crs_definition='GEOGCRS["x"', crs_definition_format="wkt2")
        self.assertVerdict(table(only_definition), "crs", "VOC-005")
        missing = geometry_field(crs_resolution="missing", crs_id=None, axis_order=None)
        self.assertIsNone(data.verdict(table(missing)))

    def test_values(self):
        self.assertVerdict(table(geometry_field(encoding="ewkb"), point(srid=4326)), "crs", "VOC-009")
        ewkb = geometry_field(encoding="ewkb", srid="4326")
        self.assertIsNone(data.verdict(table(ewkb, point(srid=4326))))
        self.assertVerdict(table(ewkb, point(srid=0)), "crs", "VOC-009")
        self.assertVerdict(table(geometry_field(), point(srid=4326)), "data_mapping", "VOC-008")
        self.assertVerdict(table(geometry_field(), b"\x01"), "data_mapping", "VOC-011")
        member = struct.pack("<BII", 1, 4, 1) + point(srid=4326)
        self.assertVerdict(table(geometry_field(types="multipoint"), member), "data_mapping", "VOC-008")
        self.assertVerdict(
            table(geometry_field(encoding="ewkb", srid="4326", types="multipoint"), member),
            "data_mapping", "VOC-009",
        )
        unknown = geometry_field(types="point,unknown", dimensions="unknown")
        line = struct.pack("<BII", 1, 2, 0)
        self.assertIsNone(data.verdict(table(unknown, line)))

    def test_fixture_errors(self):
        field = {"name": "id", "type": "int32", "nullable": False, "metadata": {}}
        cases = [
            ([field, dict(field)], [{"id": 1}]),
            ([field], [{"id": 1, "other": 2}]),
            ([field], [{"id": None}]),
            ([field], [{"id": 2**31}]),
            ([field], [{"id": True}]),
            ([dict(field, type="bool")], [{"id": 1}]),
            ([dict(field, type="float64")], [{"id": "1"}]),
            ([dict(field, type="utf8")], [{"id": 1}]),
            ([dict(field, type="binary")], [{"id": "0G"}]),
        ]
        for fields, rows in cases:
            document = {"schema_metadata": {"plenora.contract.version": "1"}, "fields": fields, "rows": rows}
            with self.subTest(fields=fields, rows=rows), self.assertRaises(data.FixtureError):
                data.verdict(document)
        ok = {"schema_metadata": {"plenora.contract.version": "1"},
              "fields": [dict(field, type="float64"), dict(field, name="b", type="bool")],
              "rows": [{"id": 1.5, "b": False}]}
        self.assertIsNone(data.verdict(ok))


class ComputationTests(unittest.TestCase):
    def test_without_definition(self):
        self.assertIsNone(data.computation_verdict(geometry_field()))
        self.assertEqual(data.computation_verdict(geometry_field(crs_id="EPSG:9999")),
                         data.Verdict("crs", "VOC-015"))

    def test_definition_without_identifier_is_undecidable_here(self):
        field = geometry_field(crs_id=None, crs_definition='GEOGCRS["x"]', crs_definition_format="wkt2")
        with self.assertRaises(data.Undecidable):
            data.computation_verdict(field)
        document = table(field)
        document["expect"] = "valid"
        self.assertEqual(data.computation_errors(document), [])
        document["computation"] = {"category": "crs", "rules": ["VOC-006"]}
        self.assertEqual(len(data.computation_errors(document)), 1)

    def test_modifications_under_the_same_identifier_are_refused(self):
        """The second reader's cases: conversion, ellipsoid unit, meridian."""
        base = ('BASEGEOGCRS["WGS 84",DATUM["d",ELLIPSOID["WGS 84",6378137,298.257223563]],'
                'ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",4326]]')
        utm33 = (f'PROJCRS["x",{base},CONVERSION["UTM 33",METHOD["Transverse Mercator"],'
                 'PARAMETER["Latitude of natural origin",0],PARAMETER["Longitude of natural origin",15],'
                 'PARAMETER["Scale factor at natural origin",0.9996],PARAMETER["False easting",500000],'
                 'PARAMETER["False northing",0]],CS[Cartesian,2],LENGTHUNIT["metre",1],ID["EPSG",32632]]')
        field = geometry_field(crs_id="EPSG:32632", crs_definition=utm33, crs_definition_format="wkt2",
                               axis_order="easting_northing")
        self.assertEqual(data.computation_verdict(field), data.Verdict("crs", "VOC-015"))
        self.assertIsNone(data.computation_verdict(geometry_field(
            crs_id="EPSG:32632", crs_definition=utm33.replace('origin",15]', 'origin",9]'),
            crs_definition_format="wkt2", axis_order="easting_northing")))
        feet = ('GEOGCRS["x",DATUM["d",ELLIPSOID["WGS 84",6378137,298.257223563,'
                'LENGTHUNIT["US survey foot",0.304800609601219]]],ID["EPSG",4326]]')
        paris = ('GEOGCRS["x",DATUM["d",ELLIPSOID["WGS 84",6378137,298.257223563]],'
                 'PRIMEM["Paris",2.5969213,ANGLEUNIT["grad",0.015707963267949]],ID["EPSG",4326]]')
        for text in (feet, paris):
            with self.subTest(text):
                self.assertEqual(
                    data.computation_verdict(geometry_field(crs_definition=text, crs_definition_format="wkt2")),
                    data.Verdict("crs", "VOC-015"),
                )

    def test_unit_identification(self):
        self.assertTrue(data.unit_decided("degree", Decimal("0.017453292519943295")))
        self.assertTrue(data.unit_decided("Meter", Decimal("1")))
        self.assertFalse(data.unit_decided("degree", Decimal("0.0175")))
        self.assertFalse(data.unit_decided("grad", Decimal("0.015707963267949")))

    def test_identifier_unknown_to_the_reference(self):
        field = geometry_field(crs_id="EPSG:2000", crs_definition='GEOGCRS["x",ID["EPSG",2000]]',
                               crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(field), data.Verdict("crs", "VOC-015"))

    def test_kind_and_unreadable_parts(self):
        projected = geometry_field(crs_definition='PROJCRS["x",ID["EPSG",4326]]', crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(projected), data.Verdict("crs", "VOC-015"))
        unreadable = geometry_field(crs_definition='GEOGCRS["x",DATUM["d",ELLIPSOID["e",1]],ID["EPSG",4326]]',
                                    crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(unreadable), data.Verdict("crs", "VOC-015"))


class VectorErrorTests(unittest.TestCase):
    def test_every_published_vector_agrees_with_the_rules(self):
        self.assertEqual(validator.validate_arrow_data_vectors(), [])

    def test_a_wrong_category_or_rule_is_reported(self):
        document = vector("invalid-ewkb-srid-differs.json")
        document["category"] = "data_mapping"
        document["rules"] = ["VOC-011"]
        errors = data.vector_errors(document)
        self.assertEqual(len(errors), 2)

    def test_an_accepted_vector_cannot_claim_a_rejection(self):
        document = vector("axis-lon-lat-epsg4326.json")
        document["expect"] = "invalid"
        self.assertEqual(data.vector_errors(document), ["must be rejected, but every rule accepts it"])
        rejected = vector("invalid-wkb-truncated.json")
        rejected["expect"] = "valid"
        self.assertIn("VOC-011", data.vector_errors(rejected)[0])

    def test_computation_verdicts(self):
        accepted = vector("crs-id-with-consistent-definition.json")
        self.assertEqual(data.vector_errors(accepted), [])
        flipped = copy.deepcopy(accepted)
        flipped["computation"] = {"category": "crs", "rules": ["VOC-015"]}
        self.assertEqual(len(data.vector_errors(flipped)), 1)
        nested = vector("crs-projcs-3003-nested-geogcs-4326.json")
        wrong = copy.deepcopy(nested)
        wrong["computation"] = "accepted"
        self.assertEqual(len(data.vector_errors(wrong)), 1)
        uncited = copy.deepcopy(nested)
        uncited["computation"] = {"category": "crs", "rules": ["VOC-005"]}
        self.assertEqual(len(data.vector_errors(uncited)), 1)
        silent = copy.deepcopy(nested)
        del silent["computation"]
        self.assertEqual(len(data.vector_errors(silent)), 1)
        plain = vector("axis-lon-lat-epsg4326.json")
        plain["computation"] = "accepted"
        self.assertEqual(data.vector_errors(plain), [])
        plain["computation"] = {"category": "crs", "rules": ["VOC-015"]}
        self.assertEqual(len(data.vector_errors(plain)), 1)
        unknown = vector("crs-unknown-identifier.json")
        unknown["computation"] = "accepted"
        self.assertEqual(len(data.vector_errors(unknown)), 1)
        missing = vector("two-geometry-fields.json")
        for field in missing["fields"][1:]:
            for key in ("crs_id", "axis_order", "srid"):
                field["metadata"].pop(f"plenora.geometry.{key}", None)
            field["metadata"]["plenora.geometry.crs_resolution"] = "missing"
            field["metadata"]["plenora.geometry.encoding"] = "wkb"
        missing["rows"][0]["site"] = None
        self.assertEqual(data.vector_errors(missing), [])
        missing["computation"] = "accepted"
        self.assertEqual(len(data.vector_errors(missing)), 1)

    def test_cited_rules_must_exist(self):
        known = validator.defined_rules()
        for rule in ("VOC-001", "VOC-015", "ARROW-002", "VOCABULARY-4", "DT-ARROW-004"):
            self.assertIn(rule, known)
        self.assertEqual(len(validator.cited_rule_errors("v", ["VOC-099", "VOC-005"], known)), 1)

    def test_a_fixture_defect_is_not_a_verdict(self):
        document = vector("axis-lon-lat-epsg4326.json")
        document["rows"][0]["id"] = None
        self.assertIn("not a buildable table", data.vector_errors(document)[0])

    def test_the_gate_reports_an_empty_directory(self):
        original = validator.ROOT
        try:
            validator.ROOT = original / "tools"
            self.assertEqual(validator.validate_arrow_data_vectors(), ["vectors/arrow-data-v1 has no vectors"])
        finally:
            validator.ROOT = original


class PrecedenceTests(unittest.TestCase):
    """ARROW-014: the first class in the fixed order is the one reported."""

    def test_version_before_every_other_class(self):
        field = geometry_field(crs_definition='GEOGCRS["x",ID["EPSG",3003]]', crs_definition_format="wkt2")
        self.assertEqual(data.verdict(table(field, b"\x01", version="2")), data.Verdict("unsupported", "ARROW-002"))

    def test_vocabulary_before_crs_and_crs_before_values(self):
        field = geometry_field(encoding=None, crs_resolution="missing")
        self.assertEqual(data.verdict(table(field, b"\x01")), data.Verdict("schema", data.VOCABULARY))
        field = geometry_field(crs_definition='GEOGCRS["x",ID["EPSG",3003]]', crs_definition_format="wkt2")
        self.assertEqual(data.verdict(table(field, b"\x01")), data.Verdict("crs", "VOC-005"))

    def test_first_row_wins_among_values(self):
        field = geometry_field(encoding="ewkb", srid="4326")
        document = table(field)
        document["rows"] = [
            {"geometry": struct.pack("<BII", 1, 2, 0).hex()},
            {"geometry": point(srid=3003).hex()},
        ]
        self.assertEqual(data.verdict(document), data.Verdict("data_mapping", "VOC-011"))
        document["rows"].reverse()
        self.assertEqual(data.verdict(document), data.Verdict("crs", "VOC-009"))

    def test_published_precedence_vectors(self):
        names = sorted(path.name for path in VECTORS.glob("invalid-precedence-*.json"))
        self.assertEqual(len(names), 4)
        for name in names:
            with self.subTest(name):
                self.assertIn("ARROW-014", vector(name)["rules"])


if __name__ == "__main__":
    unittest.main()
