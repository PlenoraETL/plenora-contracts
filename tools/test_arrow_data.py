"""Arrow Vocabulary 1.0 sections 7-12 (decision 0013): the verdicts the
validator derives for the data vectors, and the decoders behind them."""

import copy
import json
import re
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
            'PROJCRS["x",BASEGEOGCRS["y",DATUM["d",ELLIPSOID["e",6378137,298.257223563,LENGTHUNIT["metre",1]],'
            'ID["EPSG",6326]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4326]],'
            'CONVERSION["c",METHOD["Transverse Mercator"],PARAMETER["False easting",500000,'
            'LENGTHUNIT["metre",1]]],CS[Cartesian,2],AXIS["E",east,LENGTHUNIT["metre",1]],'
            'AXIS["N",north,LENGTHUNIT["metre",1]],ID["EPSG",32632]]'
        )
        parts = data.definition_parts(wkt2, "wkt2")
        self.assertEqual(parts.conversion, ("transverse_mercator", {"false_easting": Decimal("500000")}))
        self.assertEqual(parts.kind, "projected")
        self.assertEqual(parts.bases, [("EPSG", "4326")])
        self.assertEqual(parts.datums, [("EPSG", "6326")])
        self.assertEqual(parts.ellipsoid, data.WGS84)
        self.assertTrue(data.definition_parts('BOUNDCRS[SOURCECRS[GEOGCRS["x"]]]', "wkt2").datum_shift)
        self.assertEqual(data.definition_parts('VERTCRS["x"]', "wkt2").kind, "other")
        projjson = data.definition_parts(
            '{"type":"GeographicCRS","datum":{"ellipsoid":'
            '{"semi_major_axis":{"value":6378137,"unit":"metre"},"inverse_flattening":298.257223563}},'
            '"prime_meridian":{"longitude":{"value":0,"unit":"degree"}},'
            '"coordinate_system":{"subtype":"ellipsoidal","axis":[{"unit":{"name":"degree","conversion_factor":0.0174532925199433}},{"unit":{"name":"degree","conversion_factor":0.0174532925199433}}]}}',
            "projjson",
        )
        self.assertEqual(projjson.ellipsoid, (Decimal("6378137"), Decimal("298.257223563")))
        self.assertEqual(data.definition_parts('{"type":"BoundCRS"}', "projjson").kind, "other")
        good_cs = '"coordinate_system":{"subtype":"Cartesian","axis":[{"unit":"metre"},{"unit":"metre"}]}'
        geo_cs = '"coordinate_system":{"subtype":"ellipsoidal","axis":[{"unit":"degree"},{"unit":"degree"}]}'
        geo_axes = 'CS[ellipsoidal,2],AXIS["a",north],AXIS["b",east],'
        projected_axes = 'CS[Cartesian,2],AXIS["E",east],AXIS["N",north],'
        tm = '"conversion":{"method":{"name":"Transverse Mercator"},"parameters":'
        datum = '"datum":{"ellipsoid":{"semi_major_axis":1,"inverse_flattening":1}}'
        undecidable = [
            ('{"type":"ProjectedCRS"}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},"conversion":{"method":{"name":"Lambert"},"parameters":[]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[{"name":"Azimuth","value":1}]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[1]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[{"name":"False easting","value":1}]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[{"name":"False easting","value":1,"unit":"degree"}]}}',
             "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[{"name":"False easting","value":1,'
             '"unit":{"name":"foot","conversion_factor":0.3048}}]}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[{"name":"False easting","value":1,"unit":3}]}}',
             "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{},' + tm + '[]}}', "projjson"),
            ('{"type":"GeographicCRS","coordinate_system":{"subtype":"ellipsoidal","axis":[1,1]}}', "projjson"),
            ('{"type":"GeographicCRS",' + geo_cs + '}', "projjson"),
            ('{"type":"GeographicCRS",' + geo_cs + ','
             '"datum":{"ellipsoid":{"semi_major_axis":1,"semi_minor_axis":1}}}', "projjson"),
            ('{"type":"GeographicCRS",' + geo_cs + ','
             '"datum":{"ellipsoid":{"semi_major_axis":"1","inverse_flattening":1}}}', "projjson"),
            ('{"type":"GeographicCRS",' + geo_cs + ',' + datum + ','
             '"prime_meridian":{"longitude":{"value":2.3,"unit":"degree"}}}', "projjson"),
            ('{"type":"ProjectedCRS","base_crs":{' + datum + '},' + tm + '[]},' + good_cs.replace("metre", "degree", 1)
             + '}', "projjson"),
            ('GEOGCS["x",DATUM["d",SPHEROID["e",6378137]],UNIT["degree",0.0174532925199433],PRIMEM["G",0]]', "wkt"),
            ('GEOGCS["x",DATUM["d",SPHEROID["e","a","b"]],UNIT["degree",0.0174532925199433],PRIMEM["G",0]]', "wkt"),
            ('GEOGCS["x",UNIT[1]]', "wkt"),
            ('GEOGCS["x",DATUM["d",SPHEROID["e",1,1]],UNIT["degree",0.0174532925199433]]', "wkt"),
            ('GEOGCS["x",DATUM["d",SPHEROID["e",1,1]],UNIT["degree",0.0174532925199433],PRIMEM["P",2.3]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"],PROJECTION["Lambert"]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"]]', "wkt"),
            ('PROJCS["x",PROJECTION["Transverse_Mercator"]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"],PROJECTION["Transverse_Mercator"],PARAMETER["k"]]', "wkt"),
            ('PROJCS["x",GEOGCS["y"],PROJECTION["Transverse_Mercator"],PARAMETER["scale_factor",1],'
             'PARAMETER["scale_factor",1]]', "wkt"),
            ('GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1]],' + geo_axes + 'UNIT["degree",0.0174532925199433]]', "wkt2"),
            ('GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1]],' + geo_axes[:-1] + ']', "wkt2"),
            ('GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1]],' + geo_axes + 'ANGLEUNIT["degree",0.0174532925199433],'
             'LENGTHUNIT["metre",1]]', "wkt2"),
            ('GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1,ANGLEUNIT["degree",1]]],' + geo_axes +
             'ANGLEUNIT["degree",0.0174532925199433]]', "wkt2"),
            ('GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1]],PRIMEM["G",0,LENGTHUNIT["metre",1]],' + geo_axes +
             'ANGLEUNIT["degree",0.0174532925199433]]', "wkt2"),
            ('PROJCRS["x",BASEGEOGCRS["y",DATUM["d",ELLIPSOID["e",1,1]]],CONVERSION["c",METHOD["Transverse Mercator"],'
             'PARAMETER["False easting",1]],' + projected_axes + 'LENGTHUNIT["metre",1]]', "wkt2"),
            ('PROJCRS["x",BASEGEOGCRS["y",DATUM["d",ELLIPSOID["e",1,1]]],CONVERSION["c",METHOD["Transverse Mercator"],'
             'PARAMETER["False easting",1,ANGLEUNIT["degree",0.0174532925199433]]],' + projected_axes
             + 'LENGTHUNIT["metre",1]]', "wkt2"),
            ('GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1]],' + geo_axes + 'NAMELESS[1],ANGLEUNIT["x",1]]', "wkt2"),
            ('GEOGCRS["x",METHOD[1]]', "wkt2"),
        ]
        for text, kind in undecidable:
            with self.subTest(text), self.assertRaises(data.Undecidable):
                data.definition_parts(text, kind)


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
            {"plenora.field_id": "1\n"},
            {"srid": "4326\n"},
        ]
        for metadata in cases:
            with self.subTest(metadata):
                self.assertVerdict(table(geometry_field(**metadata)), "schema", data.VOCABULARY)
        for metadata in ({"crs_id": ""}, {"crs_id": "4326"}, {"types": ""}, {"plenora.geometry.sird": "4326"}):
            with self.subTest(metadata):
                self.assertVerdict(table(geometry_field(**metadata)), "schema", "GEO-016")
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
        self.assertVerdict(table(only_definition), "crs", "GEO-005")
        missing = geometry_field(crs_resolution="missing", crs_id=None, axis_order=None)
        self.assertIsNone(data.verdict(table(missing)))

    def test_values(self):
        self.assertVerdict(table(geometry_field(encoding="ewkb"), point(srid=4326)), "crs", "GEO-009")
        ewkb = geometry_field(encoding="ewkb", srid="4326")
        self.assertIsNone(data.verdict(table(ewkb, point(srid=4326))))
        self.assertVerdict(table(ewkb, point(srid=0)), "crs", "GEO-009")
        self.assertVerdict(table(geometry_field(), point(srid=4326)), "data_mapping", "GEO-008")
        self.assertVerdict(table(geometry_field(), b"\x01"), "data_mapping", "GEO-011")
        member = struct.pack("<BII", 1, 4, 1) + point(srid=4326)
        self.assertVerdict(table(geometry_field(types="multipoint"), member), "data_mapping", "GEO-008")
        self.assertVerdict(
            table(geometry_field(encoding="ewkb", srid="4326", types="multipoint"), member),
            "data_mapping", "GEO-009",
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
                         data.Verdict("crs", "GEO-015"))

    def test_definition_without_identifier_is_undecidable_here(self):
        field = geometry_field(crs_id=None, crs_definition='GEOGCRS["x"]', crs_definition_format="wkt2")
        with self.assertRaises(data.Undecidable):
            data.computation_verdict(field)
        document = table(field)
        document["expect"] = "valid"
        self.assertEqual(data.computation_errors(document), [])
        document["computation"] = {"category": "crs", "rules": ["GEO-006"]}
        self.assertEqual(len(data.computation_errors(document)), 1)

    def test_modifications_under_the_same_identifier_are_refused(self):
        """Second readings: conversion, ellipsoid unit, meridian, datum, units."""
        base = ('BASEGEOGCRS["WGS 84",DATUM["d",ELLIPSOID["WGS 84",6378137,298.257223563],ID["EPSG",6326]],'
                'ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",4326]]')
        deg = 'ANGLEUNIT["degree",0.0174532925199433]'
        utm33 = (f'PROJCRS["x",{base},CONVERSION["UTM 33",METHOD["Transverse Mercator"],'
                 f'PARAMETER["Latitude of natural origin",0,{deg}],PARAMETER["Longitude of natural origin",15,{deg}],'
                 'PARAMETER["Scale factor at natural origin",0.9996,SCALEUNIT["unity",1]],'
                 'PARAMETER["False easting",500000,LENGTHUNIT["metre",1]],'
                 'PARAMETER["False northing",0,LENGTHUNIT["metre",1]]],'
                 'CS[Cartesian,2],AXIS["E",east],AXIS["N",north],LENGTHUNIT["metre",1],ID["EPSG",32632]]')

        def utm(text):
            return geometry_field(crs_id="EPSG:32632", crs_definition=text, crs_definition_format="wkt2",
                                  axis_order="easting_northing")

        self.assertEqual(data.computation_verdict(utm(utm33)), data.Verdict("crs", "GEO-015"))
        utm32 = utm33.replace('origin",15,', 'origin",9,')
        self.assertIsNone(data.computation_verdict(utm(utm32)))
        self.assertEqual(data.computation_verdict(utm(utm32.replace('ID["EPSG",6326]', 'ID["EPSG",6230]'))),
                         data.Verdict("crs", "GEO-015"))
        self.assertEqual(data.computation_verdict(utm(utm32.replace(',ID["EPSG",4326]]', ',ID["EPSG",4258]]'))),
                         data.Verdict("crs", "GEO-015"))
        feet = ('GEOGCRS["x",DATUM["d",ELLIPSOID["WGS 84",6378137,298.257223563,'
                'LENGTHUNIT["US survey foot",0.304800609601219]]],CS[ellipsoidal,2],AXIS["a",north],AXIS["b",east],'
                'ANGLEUNIT["degree",0.0174532925199433],'
                'ID["EPSG",4326]]')
        paris = ('GEOGCRS["x",DATUM["d",ELLIPSOID["WGS 84",6378137,298.257223563]],'
                 'PRIMEM["Paris",2.5969213,ANGLEUNIT["grad",0.015707963267949]],'
                 'CS[ellipsoidal,2],AXIS["a",north],AXIS["b",east],ANGLEUNIT["degree",0.0174532925199433],'
                 'ID["EPSG",4326]]')
        for text in (feet, paris):
            with self.subTest(text):
                self.assertEqual(
                    data.computation_verdict(geometry_field(crs_definition=text, crs_definition_format="wkt2")),
                    data.Verdict("crs", "GEO-015"),
                )

    def test_unit_identification(self):
        """GEO-017: name, factor and quantity; the degree has two exact spellings."""
        self.assertTrue(data.unit_decided("degree", Decimal("0.017453292519943295"), "angle"))
        self.assertTrue(data.unit_decided("degree", Decimal("1.74532925199433E-2"), "angle"))
        self.assertTrue(data.unit_decided("Meter", Decimal("1.0"), "length"))
        self.assertFalse(data.unit_decided("metre", Decimal("1"), "angle"))
        self.assertFalse(data.unit_decided("degree", Decimal("0.01745329251994330001"), "angle"))
        self.assertFalse(data.unit_decided("grad", Decimal("0.015707963267949"), "angle"))

    def test_identifier_unknown_to_the_reference(self):
        field = geometry_field(crs_id="EPSG:2000", crs_definition='GEOGCRS["x",ID["EPSG",2000]]',
                               crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(field), data.Verdict("crs", "GEO-015"))

    def test_kind_and_unreadable_parts(self):
        projected = geometry_field(crs_definition='PROJCRS["x",ID["EPSG",4326]]', crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(projected), data.Verdict("crs", "GEO-015"))
        # An ellipsoid with one value is outside the grammar (GEO-019); one
        # in the grammar without a coordinate system unit is undecidable.
        unreadable = geometry_field(crs_definition='GEOGCRS["x",DATUM["d",ELLIPSOID["e",1]],ID["EPSG",4326]]',
                                    crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(unreadable), data.Verdict("crs", "GEO-019"))
        unitless = geometry_field(crs_definition='GEOGCRS["x",DATUM["d",ELLIPSOID["e",1,1]],ID["EPSG",4326]]',
                                  crs_definition_format="wkt2")
        self.assertEqual(data.computation_verdict(unitless), data.Verdict("crs", "GEO-015"))


class VectorErrorTests(unittest.TestCase):
    def test_every_published_vector_agrees_with_the_rules(self):
        self.assertEqual(validator.validate_arrow_data_vectors(), [])

    def test_a_wrong_category_or_rule_is_reported(self):
        document = vector("invalid-ewkb-srid-differs.json")
        document["category"] = "data_mapping"
        document["rules"] = ["GEO-011"]
        errors = data.vector_errors(document)
        self.assertEqual(len(errors), 2)

    def test_an_accepted_vector_cannot_claim_a_rejection(self):
        document = vector("axis-lon-lat-epsg4326.json")
        document["expect"] = "invalid"
        self.assertEqual(data.vector_errors(document), ["must be rejected, but every rule accepts it"])
        rejected = vector("invalid-wkb-truncated.json")
        rejected["expect"] = "valid"
        self.assertIn("GEO-011", data.vector_errors(rejected)[0])

    def test_computation_verdicts(self):
        accepted = vector("crs-id-with-consistent-definition.json")
        self.assertEqual(data.vector_errors(accepted), [])
        flipped = copy.deepcopy(accepted)
        flipped["computation"] = {"category": "crs", "rules": ["GEO-015"]}
        self.assertEqual(len(data.vector_errors(flipped)), 1)
        nested = vector("crs-projcs-3003-nested-geogcs-4326.json")
        wrong = copy.deepcopy(nested)
        wrong["computation"] = "accepted"
        self.assertEqual(len(data.vector_errors(wrong)), 1)
        uncited = copy.deepcopy(nested)
        uncited["computation"] = {"category": "crs", "rules": ["GEO-005"]}
        self.assertEqual(len(data.vector_errors(uncited)), 1)
        silent = copy.deepcopy(nested)
        del silent["computation"]
        self.assertEqual(len(data.vector_errors(silent)), 1)
        plain = vector("axis-lon-lat-epsg4326.json")
        plain["computation"] = "accepted"
        self.assertEqual(len(data.vector_errors(plain)), 1)

    def test_cited_rules_must_exist(self):
        known = validator.defined_rules()
        for rule in ("GEO-001", "GEO-015", "ARROW-002", "VOCABULARY-4", "DT-ARROW-004"):
            self.assertIn(rule, known)
        self.assertEqual(len(validator.cited_rule_errors("v", ["GEO-099", "GEO-005"], known)), 1)

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


class LocalAuthorityTests(unittest.TestCase):
    """GEO-020: a local catalog identifier is never resolved and never
    computed with."""

    def field(self, crs_id, resolution, **extra):
        vector = json.loads((VECTORS / "crs-local-authority-postgis.json").read_text(encoding="utf-8"))
        field = vector["fields"][1]
        field["metadata"]["plenora.geometry.crs_id"] = crs_id
        field["metadata"]["plenora.geometry.crs_resolution"] = resolution
        field["metadata"].update(extra)
        return field

    def test_the_closed_list(self):
        for crs_id in ("POSTGIS:1", "postgis:1", "MySQL:4326", "MARIADB:1", "MSSQL:1", "ORACLE:1", "DB2:1",
                       "SQLITE:1"):
            with self.subTest(crs_id):
                self.assertTrue(data.is_local_authority(crs_id))
        for crs_id in ("EPSG:4326", "POSTGISX:1", "XPOSTGIS:1", "ESRI:102100", "OGC:CRS84", "POSTGIS"):
            with self.subTest(crs_id):
                self.assertFalse(data.is_local_authority(crs_id))

    def test_never_resolved(self):
        self.assertIsNone(data._crs([self.field("POSTGIS:4326", "declared_unresolved")]))
        self.assertEqual(data._crs([self.field("PostGIS:4326", "resolved")]), data.Verdict("crs", "GEO-020"))
        self.assertIsNone(data._crs([self.field("EPSG:4326", "resolved")]))

    def test_never_computed_with(self):
        self.assertEqual(data.computation_verdict(self.field("MYSQL:4326", "declared_unresolved")),
                         data.Verdict("crs", "GEO-020"))
        # Not even with a definition the component would verify.
        definition = json.loads((VECTORS / "crs-proj-epsg-4326-wkt1.json").read_text(encoding="utf-8"))
        metadata = definition["fields"][1]["metadata"]
        field = self.field("POSTGIS:4326", "declared_unresolved", **{
            key: metadata[key] for key in ("plenora.geometry.crs_definition", "plenora.geometry.crs_definition_format")
        })
        self.assertEqual(data.computation_verdict(field), data.Verdict("crs", "GEO-020"))
        self.assertIsNone(data.computation_verdict(self.field("EPSG:4326", "resolved")))


class ClosedGrammarTests(unittest.TestCase):
    """GEO-019, generatively: an unknown node or member anywhere in a verified
    definition makes it undecidable."""

    def accepted(self):
        for path in sorted(VECTORS.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("computation") == "accepted":
                for field in document["fields"]:
                    if "plenora.geometry.crs_definition" in field["metadata"]:
                        yield path.name, field

    def test_an_unknown_wkt_node_anywhere(self):
        count = 0
        for name, field in self.accepted():
            metadata = field["metadata"]
            if metadata["plenora.geometry.crs_definition_format"] == "projjson":
                continue
            text = metadata["plenora.geometry.crs_definition"]
            for position, character in enumerate(text):
                if character != "[":
                    continue
                mutated = copy.deepcopy(field)
                mutated["metadata"]["plenora.geometry.crs_definition"] = (
                    text[:position + 1] + "ZZUNKNOWN[1]," + text[position + 1:]
                )
                with self.subTest(name=name, position=position):
                    at_input = data._crs([mutated])
                    if at_input is not None:
                        # Inside a root identifier: not even a conforming input.
                        self.assertEqual(at_input, data.Verdict("crs", "GEO-005"))
                    else:
                        self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-019"))
                count += 1
        self.assertGreater(count, 50)

    def test_an_unknown_projjson_member_anywhere(self):
        count = 0
        for name, field in self.accepted():
            metadata = field["metadata"]
            if metadata["plenora.geometry.crs_definition_format"] != "projjson":
                continue
            root = json.loads(metadata["plenora.geometry.crs_definition"])

            def objects(value, trail=()):
                if isinstance(value, dict):
                    yield trail
                    for key, child in value.items():
                        yield from objects(child, trail + (key,))
                elif isinstance(value, list):
                    for index, child in enumerate(value):
                        yield from objects(child, trail + (index,))

            for trail in list(objects(root)):
                mutated_root = copy.deepcopy(root)
                target = mutated_root
                for step in trail:
                    target = target[step]
                target["zz_unknown"] = 1
                mutated = copy.deepcopy(field)
                mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(mutated_root)
                with self.subTest(name=name, trail=trail):
                    self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-019"))
                count += 1
        self.assertGreater(count, 10)

    def test_only_the_reference_ensemble(self):
        vector = json.loads((VECTORS / "crs-proj-epsg-4326-projjson.json").read_text(encoding="utf-8"))
        field = vector["fields"][1]
        root = json.loads(field["metadata"]["plenora.geometry.crs_definition"])

        def verdict(change):
            variant = copy.deepcopy(root)
            change(variant["datum_ensemble"])
            mutated = copy.deepcopy(field)
            mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(variant)
            return data.computation_verdict(mutated)

        self.assertIsNone(verdict(lambda ensemble: None))
        changes = {
            "member identifier": lambda e: e["members"][0]["id"].update(code=1),
            "member name": lambda e: e["members"][0].update(name="World Geodetic System 1984 (G9999)"),
            "member added": lambda e: e["members"].append({"name": "World Geodetic System 1984 (G9999)"}),
            "members reordered": lambda e: e["members"].reverse(),
            "ensemble identifier": lambda e: e["id"].update(code=6258),
            "ensemble name": lambda e: e.update(name="European Terrestrial Reference System 1989 ensemble"),
            "accuracy as a number": lambda e: e.update(accuracy=2.0),
            "accuracy missing": lambda e: e.pop("accuracy"),
            "ensemble type": lambda e: e.update(type="DynamicGeodeticReferenceFrame"),
        }
        for name, change in changes.items():
            with self.subTest(name):
                self.assertEqual(verdict(change), data.Verdict("crs", "GEO-019"))
        # Without member identifiers, as WKT 2 writes them, and with the
        # accuracy spelled otherwise, it is the same ensemble.
        def strip(ensemble):
            for member in ensemble["members"]:
                member.pop("id")
            ensemble["accuracy"] = "2"
        self.assertIsNone(verdict(strip))
        both = copy.deepcopy(root)
        both["datum"] = {"name": "World Geodetic System 1984", "ellipsoid": both["datum_ensemble"]["ellipsoid"]}
        mutated = copy.deepcopy(field)
        mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(both)
        self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-019"))

    def test_a_datum_without_identifier_by_its_name(self):
        vector = json.loads((VECTORS / "crs-proj-epsg-3003-projjson.json").read_text(encoding="utf-8"))
        field = vector["fields"][1]
        root = json.loads(field["metadata"]["plenora.geometry.crs_definition"])
        for name, expected in (("Monte_Mario", None), ("MONTE MARIO", None),
                               ("European Datum 1950", data.Verdict("crs", "GEO-015"))):
            variant = copy.deepcopy(root)
            variant["base_crs"]["datum"]["name"] = name
            mutated = copy.deepcopy(field)
            mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(variant)
            with self.subTest(name):
                self.assertEqual(data.computation_verdict(mutated), expected)
        nameless = copy.deepcopy(root)
        del nameless["base_crs"]["datum"]["name"]
        mutated = copy.deepcopy(field)
        mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(nameless)
        self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-015"))

    def expect_outside(self, field, text, where):
        mutated = copy.deepcopy(field)
        mutated["metadata"]["plenora.geometry.crs_definition"] = text
        with self.subTest(where=where):
            at_input = data._crs([mutated])
            if at_input is not None:
                # In a root identifier: not even a conforming input.
                self.assertEqual(at_input, data.Verdict("crs", "GEO-005"))
            else:
                self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-019"))

    def test_every_projjson_value_of_another_kind(self):
        """GEO-019 closes the values too: every member, at any depth, given
        a value of another JSON kind is outside the grammar. A code is a
        number or a string, so that swap alone is admitted."""
        others = {"string": "x", "number": 1, "true": True, "null": None, "object": {}, "array": []}

        def kind(value):
            if value is None:
                return "null"
            if isinstance(value, bool):
                return "true"
            if isinstance(value, str):
                return "string"
            if isinstance(value, (int, float)):
                return "number"
            return "object" if isinstance(value, dict) else "array"

        def places(value, trail=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield trail + (key,)
                    yield from places(child, trail + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield trail + (index,)
                    yield from places(child, trail + (index,))

        count = 0
        for name, field in self.accepted():
            if field["metadata"]["plenora.geometry.crs_definition_format"] != "projjson":
                continue
            root = json.loads(field["metadata"]["plenora.geometry.crs_definition"])
            for trail in list(places(root)):
                parent = root
                for step in trail[:-1]:
                    parent = parent[step]
                current = parent[trail[-1]]
                for other, replacement in others.items():
                    if other == kind(current):
                        continue
                    if trail[-1] == "code" and {other, kind(current)} == {"string", "number"}:
                        continue
                    mutated_root = copy.deepcopy(root)
                    target = mutated_root
                    for step in trail[:-1]:
                        target = target[step]
                    target[trail[-1]] = replacement
                    self.expect_outside(field, json.dumps(mutated_root), (name, trail, other))
                    count += 1
        self.assertGreater(count, 1000)

    def test_every_wkt_value_of_another_kind(self):
        """GEO-019 in WKT: every value given another kind (a text for a
        number or a word, a number for a text) or replaced by a node is
        outside the grammar; an identifier code is a number or a text."""

        def text(node):
            items = []
            for item in node.items:
                if isinstance(item, data._Node):
                    items.append(text(item))
                elif item[0] == "string":
                    items.append('"' + item[1].replace('"', '""') + '"')
                else:
                    items.append(item[1])
            return node.keyword + "[" + ",".join(items) + "]"

        def scalars(node, trail=()):
            for index, item in enumerate(node.items):
                if isinstance(item, data._Node):
                    yield from scalars(item, trail + (index,))
                else:
                    yield trail + (index,), node.keyword.upper(), item[0]

        count = 0
        for name, field in self.accepted():
            definition_format = field["metadata"]["plenora.geometry.crs_definition_format"]
            if definition_format == "projjson":
                continue
            root = data.parse_wkt(field["metadata"]["plenora.geometry.crs_definition"])
            self.assertEqual(data.parse_wkt(text(root)), root)
            for trail, keyword, current in list(scalars(root)):
                replacements = {"string": ("number", "1"), "number": ("string", "x"), "word": ("string", "x")}
                for replacement in (replacements[current], "node"):
                    if keyword in ("ID", "AUTHORITY") and trail[-1] == 1 and replacement != "node":
                        continue
                    mutated = copy.deepcopy(root)
                    parent = mutated
                    for step in trail[:-1]:
                        parent = parent.items[step]
                    parent.items[trail[-1]] = (
                        data._Node("ZZ", [("number", "1")]) if replacement == "node" else replacement
                    )
                    self.expect_outside(field, text(mutated), (name, trail, replacement))
                    count += 1
        self.assertGreater(count, 500)

    def test_every_unit_of_every_coordinate_system(self):
        """The base CRS's units are compared too (GEO-015): a radian on the
        base geographic CRS is not decided."""
        radian = {"type": "AngularUnit", "name": "radian", "conversion_factor": 1}
        vector = json.loads((VECTORS / "crs-proj-epsg-32632-projjson.json").read_text(encoding="utf-8"))
        field = vector["fields"][1]
        root = json.loads(field["metadata"]["plenora.geometry.crs_definition"])
        for index in range(len(root["base_crs"]["coordinate_system"]["axis"])):
            variant = copy.deepcopy(root)
            variant["base_crs"]["coordinate_system"]["axis"][index]["unit"] = radian
            mutated = copy.deepcopy(field)
            mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(variant)
            with self.subTest(index):
                self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-015"))
        broken = copy.deepcopy(root)
        broken["base_crs"]["coordinate_system"]["axis"] = []
        mutated = copy.deepcopy(field)
        mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(broken)
        self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-015"))
        wkt = json.loads((VECTORS / "crs-proj-epsg-3003-wkt2.json").read_text(encoding="utf-8"))
        wfield = wkt["fields"][1]
        text = wfield["metadata"]["plenora.geometry.crs_definition"]
        for old, new in (
            ('ID["EPSG",4265]]', 'ANGLEUNIT["radian",1],ID["EPSG",4265]]'),
            ('PRIMEM["Greenwich",0,\n            ANGLEUNIT["degree",0.0174532925199433]]',
             'PRIMEM["Greenwich",0,\n            ANGLEUNIT["radian",1]]'),
        ):
            self.assertIn(old, text)
            mutated = copy.deepcopy(wfield)
            mutated["metadata"]["plenora.geometry.crs_definition"] = text.replace(old, new, 1)
            with self.subTest(new):
                self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-015"))

    def test_the_reported_extensions(self):
        wkt2 = json.loads((VECTORS / "crs-id-with-consistent-definition.json").read_text(encoding="utf-8"))
        field = wkt2["fields"][1]
        text = field["metadata"]["plenora.geometry.crs_definition"]
        undecidable = (
            "DYNAMIC[FRAMEEPOCH[2020]],",
            'USAGE[SCOPE["x"],AREA["y"],BBOX[0,0,1,1],VERTICALEXTENT[0,1]],',
            'USAGE[SCOPE["x"],SCOPE["y"]],',
            'USAGE[SCOPE[1]],',
            'USAGE[BBOX[0,0,1]],',
            'USAGE["x"],',
            'REMARK["r",1],',
            'REMARK[ID["EPSG",1]],',
        )
        for extension in undecidable:
            mutated = copy.deepcopy(field)
            mutated["metadata"]["plenora.geometry.crs_definition"] = text.replace("DATUM[", extension + "DATUM[", 1)
            with self.subTest(extension):
                self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-019"))
        # Usage metadata is ignorable: it never changes the verdict.
        ignorable = (
            'USAGE[SCOPE["x"],AREA["y"],BBOX[0,0,1,1],ID["EPSG",1]],USAGE[SCOPE["z"]],',
            'SCOPE["x"],AREA["y"],BBOX[-90,-180,90,180],REMARK["r"],',
        )
        for extension in ignorable:
            mutated = copy.deepcopy(field)
            mutated["metadata"]["plenora.geometry.crs_definition"] = text.replace("DATUM[", extension + "DATUM[", 1)
            with self.subTest(extension):
                self.assertIsNone(data.computation_verdict(mutated))
        # An axis unit is admitted and then compared: a grad is not decided.
        axis_unit = copy.deepcopy(field)
        axis_unit["metadata"]["plenora.geometry.crs_definition"] = text.replace(
            "north]", 'north,ANGLEUNIT["grad",0.015707963267948967]]', 1)
        self.assertEqual(data.computation_verdict(axis_unit), data.Verdict("crs", "GEO-015"))
        for order in ('north,ORDER[2]]', 'north,ORDER[1]]'):
            reordered = copy.deepcopy(field)
            reordered["metadata"]["plenora.geometry.crs_definition"] = text.replace("north]", order, 1)
            with self.subTest(order):
                # An order on one axis only, or one that reorders, is outside.
                self.assertEqual(data.computation_verdict(reordered), data.Verdict("crs", "GEO-019"))
        projjson = json.loads((VECTORS / "crs-projjson-consistent-32632.json").read_text(encoding="utf-8"))
        pfield = projjson["fields"][1]
        root = json.loads(pfield["metadata"]["plenora.geometry.crs_definition"])
        dynamic = copy.deepcopy(root)
        dynamic["base_crs"]["datum"]["type"] = "DynamicGeodeticReferenceFrame"
        ensemble = copy.deepcopy(root)
        ensemble["base_crs"]["datum_ensemble"] = ensemble["base_crs"].pop("datum")
        for variant in (dynamic, ensemble):
            mutated = copy.deepcopy(pfield)
            mutated["metadata"]["plenora.geometry.crs_definition"] = json.dumps(variant)
            self.assertEqual(data.computation_verdict(mutated), data.Verdict("crs", "GEO-019"))


class RequiredPartsTests(unittest.TestCase):
    """GEO-017: a unit or a coordinate system part the rules require, when
    missing, makes the definition undecidable; it is never assumed."""

    def field(self, name):
        return json.loads((VECTORS / name).read_text(encoding="utf-8"))["fields"][1]

    def verdict_of(self, field, text):
        mutated = copy.deepcopy(field)
        mutated["metadata"]["plenora.geometry.crs_definition"] = text
        return data.computation_verdict(mutated)

    def assertUndecidable(self, field, text):
        self.assertEqual(self.verdict_of(field, text), data.Verdict("crs", "GEO-015"))

    def test_the_wkt2_prime_meridian_carries_its_unit(self):
        for name in ("crs-proj-epsg-4326-wkt2.json", "crs-proj-epsg-3003-wkt2.json"):
            field = self.field(name)
            text = field["metadata"]["plenora.geometry.crs_definition"]
            found = re.search(r'PRIMEM\["Greenwich",0,\s*ANGLEUNIT\["degree",0\.0174532925199433\]\]', text)
            self.assertIsNotNone(found, name)
            with self.subTest(name):
                self.assertUndecidable(field, text.replace(found.group(0), 'PRIMEM["Greenwich",0]'))

    def test_the_projjson_prime_meridian_carries_its_unit(self):
        field = self.field("crs-proj-epsg-3003-projjson.json")
        root = json.loads(field["metadata"]["plenora.geometry.crs_definition"])
        for meridian in ({"name": "Greenwich", "longitude": 0}, {"name": "Greenwich"}):
            variant = copy.deepcopy(root)
            variant["base_crs"]["datum"]["prime_meridian"] = meridian
            with self.subTest(meridian):
                self.assertUndecidable(field, json.dumps(variant))
        variant = copy.deepcopy(root)
        variant["base_crs"]["datum"]["prime_meridian"] = {
            "name": "Greenwich", "longitude": {"value": 0, "unit": "degree"}}
        self.assertIsNone(self.verdict_of(field, json.dumps(variant)))

    def test_every_unit_removed_from_a_verified_definition(self):
        """Generatively: removing any unit node or member from a verified
        definition makes it undecidable, except where GEO-017 states the
        unit implicitly (an ellipsoid in metres; a WKT 2 base CRS, which has
        no coordinate system of its own)."""
        implicit = ("ELLIPSOID", "BASEGEOGCRS")
        count = 0
        for name, field in ClosedGrammarTests().accepted():
            text = field["metadata"]["plenora.geometry.crs_definition"]
            if field["metadata"]["plenora.geometry.crs_definition_format"] == "projjson":
                root = json.loads(text)
                for path in _unit_paths(root):
                    variant = copy.deepcopy(root)
                    holder = variant
                    for key in path[:-1]:
                        holder = holder[key]
                    del holder[path[-1]]
                    count += 1
                    with self.subTest(name=name, path=path):
                        self.assertUndecidable(field, json.dumps(variant))
                continue
            for start, end, parent in _wkt_unit_nodes(text):
                if parent in implicit:
                    continue
                count += 1
                with self.subTest(name=name, at=start):
                    self.assertUndecidable(field, text[:start] + text[end:])
        self.assertGreater(count, 20)

    def test_the_coordinate_system_is_two_dimensional_and_complete(self):
        field = self.field("crs-id-with-consistent-definition.json")
        text = field["metadata"]["plenora.geometry.crs_definition"]
        deg = 'ANGLEUNIT["degree",0.0174532925199433]'
        self.assertIsNone(self.verdict_of(field, text))
        lon = ',AXIS["geodetic longitude (Lon)",east]'
        variants = {
            # The unit on one axis only: the other axis has none.
            "axis without unit": text.replace(lon, "").replace("," + deg + ",ID", ",ID").replace(
                "north]", "north," + deg + "]"),
            "three dimensions": text.replace("ellipsoidal,2", "ellipsoidal,3"),
            "one axis": text.replace(lon, ""),
            "no axes": text.replace(lon, "").replace(',AXIS["geodetic latitude (Lat)",north]', ""),
            "no coordinate system": text.replace(",CS[ellipsoidal,2]", ""),
            "Cartesian": text.replace("ellipsoidal,2", "Cartesian,2"),
        }
        for label, variant in variants.items():
            self.assertNotEqual(variant, text, label)
            with self.subTest(label):
                self.assertUndecidable(field, variant)
        wkt1 = self.field("crs-id-with-consistent-wkt1-definition.json")
        wtext = wkt1["metadata"]["plenora.geometry.crs_definition"]
        self.assertIsNone(self.verdict_of(wkt1, wtext))
        no_axes = wtext.replace(',AXIS["Latitude",NORTH],AXIS["Longitude",EAST]', "")
        self.assertNotEqual(no_axes, wtext)
        self.assertIsNone(self.verdict_of(wkt1, no_axes))
        for label, variant in {
            "one axis": wtext.replace(',AXIS["Longitude",EAST]', ""),
            "three axes": wtext.replace('EAST]', 'EAST],AXIS["h",UP]'),
        }.items():
            self.assertNotEqual(variant, wtext, label)
            with self.subTest(label):
                self.assertUndecidable(wkt1, variant)
        projjson = self.field("crs-proj-epsg-3003-projjson.json")
        root = json.loads(projjson["metadata"]["plenora.geometry.crs_definition"])
        mutations = {
            "projected ellipsoidal": lambda r: r["coordinate_system"].__setitem__("subtype", "ellipsoidal"),
            "no subtype": lambda r: r["coordinate_system"].pop("subtype"),
            "one axis": lambda r: r["coordinate_system"]["axis"].pop(),
            "base Cartesian": lambda r: r["base_crs"]["coordinate_system"].__setitem__("subtype", "Cartesian"),
            "base one axis": lambda r: r["base_crs"]["coordinate_system"]["axis"].pop(),
        }
        for label, mutate in mutations.items():
            variant = copy.deepcopy(root)
            mutate(variant)
            with self.subTest(label):
                self.assertUndecidable(projjson, json.dumps(variant))

    def test_a_projjson_code_is_an_integer_literal(self):
        """`str` of a JSON number is not its code: `6326.0` and `6.326E3`
        are refused like a non-integer WKT code, never compared as text."""
        from decimal import Decimal
        import crs_grammar
        self.assertEqual(crs_grammar._projjson_ids({"id": {"authority": "EPSG", "code": 6326}}),
                         [("EPSG", "6326")])
        for code in (Decimal("6326.0"), Decimal("6.326E3")):
            with self.subTest(code=str(code)), self.assertRaises(crs_grammar.Outside):
                crs_grammar._projjson_ids({"id": {"authority": "EPSG", "code": code}})
        field = self.field("crs-proj-epsg-4326-projjson.json")
        text = field["metadata"]["plenora.geometry.crs_definition"]
        self.assertIn('"code": 1166', text)
        for written in ("1166.0", "1.166E3"):
            with self.subTest(written):
                self.assertEqual(self.verdict_of(field, text.replace('"code": 1166', '"code": ' + written, 1)),
                                 data.Verdict("crs", "GEO-019"))


def _unit_paths(value, path=()):
    """Every `unit` member of a PROJJSON document."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "unit":
                yield path + (key,)
            yield from _unit_paths(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _unit_paths(item, path + (index,))


def _wkt_unit_nodes(text):
    """The span of every unit node of a WKT text, with its leading comma,
    and the keyword of the node that holds it."""
    stack = []
    for found in re.finditer(r'[A-Za-z][A-Za-z0-9_]*\[|\]|"(?:[^"]|"")*"', text):
        token = found.group(0)
        if token.startswith('"'):
            continue
        if token == "]":
            keyword, start = stack.pop()
            if keyword in ("ANGLEUNIT", "LENGTHUNIT", "SCALEUNIT", "UNIT"):
                begin = start
                while text[begin - 1] in " \n":
                    begin -= 1
                if text[begin - 1] == ",":
                    begin -= 1
                yield begin, found.end(), stack[-1][0]
            continue
        stack.append((token[:-1].upper(), found.start()))

if __name__ == "__main__":
    unittest.main()
