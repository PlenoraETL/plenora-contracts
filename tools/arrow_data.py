"""Verdicts on Arrow data vectors (Arrow Vocabulary 1.0, sections 4 and 7-12).

A vector is a schema fixture with row values. `verdict` derives, from the
rules alone, whether a consumer of the vocabulary accepts it and, when it
does not, the category and the rule that decide the rejection. The validator
compares that verdict with the one the vector states, so a vector cannot
claim a category the rules do not give.

The checks run in a fixed order: the schema contract version (ARROW-001,
ARROW-002), the well-formedness of the vocabulary (section 4), the CRS state
(section 4, VOC-005), then each geometry value in row order and, within a
row, in field order (VOC-008, VOC-009, VOC-011). The first failure is the
verdict; every vector of this version has a single defect.

`FixtureError` is a defect of the vector itself (a value that does not fit
its Arrow type, a null in a non-nullable field): no consumer could even build
the table, so it is not a verdict on the vocabulary.
"""

from __future__ import annotations

import json
import re
import struct
from decimal import Decimal
from typing import Any, NamedTuple


class FixtureError(Exception):
    """The vector cannot be built as an Arrow table."""


class Malformed(Exception):
    """A WKB or EWKB value, or a CRS definition, that is not well-formed."""


class SridOnMember(Malformed):
    """An SRID flag on a member geometry: VOC-008 under `wkb`, VOC-009 under
    `ewkb`."""


class Undecidable(Malformed):
    """Well-formed CRS definition whose parts VOC-015 cannot decide."""


class Verdict(NamedTuple):
    category: str
    rule: str


GEOMETRY_TYPES = {
    1: "point",
    2: "linestring",
    3: "polygon",
    4: "multipoint",
    5: "multilinestring",
    6: "multipolygon",
    7: "geometrycollection",
    8: "circularstring",
    9: "compoundcurve",
    10: "curvepolygon",
    11: "multicurve",
    12: "multisurface",
    15: "polyhedralsurface",
    16: "tin",
    17: "triangle",
}
CANONICAL_TYPES = [
    "point", "linestring", "polygon", "multipoint", "multilinestring",
    "multipolygon", "geometrycollection", "circularstring", "compoundcurve",
    "curvepolygon", "multicurve", "multisurface", "polyhedralsurface", "tin",
    "triangle", "unknown",
]
# The members a container admits; `None` admits any geometry.
MEMBERS: dict[str, set[str] | None] = {
    "multipoint": {"point"},
    "multilinestring": {"linestring"},
    "multipolygon": {"polygon"},
    "geometrycollection": None,
    "compoundcurve": {"linestring", "circularstring"},
    "curvepolygon": {"linestring", "circularstring", "compoundcurve"},
    "multicurve": {"linestring", "circularstring", "compoundcurve"},
    "multisurface": {"polygon", "curvepolygon"},
    "polyhedralsurface": {"polygon"},
    "tin": {"triangle"},
}
DIMENSIONS = {(False, False): "xy", (True, False): "xyz", (False, True): "xym", (True, True): "xyzm"}
ISO_DIMENSIONS = {0: (False, False), 1: (True, False), 2: (False, True), 3: (True, True)}
FLAG_Z = 0x80000000
FLAG_M = 0x40000000
FLAG_SRID = 0x20000000
MAX_DEPTH = 32


class Geometry(NamedTuple):
    type: str
    dimensions: str
    srid: int | None


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise Malformed("value ends early")
        chunk = self.data[self.pos:self.pos + size]
        self.pos += size
        return chunk

    def remaining(self) -> int:
        return len(self.data) - self.pos


def _geometry(reader: _Reader, depth: int, outer: bool) -> Geometry:
    if depth > MAX_DEPTH:
        raise Malformed("nesting too deep")
    order = reader.take(1)[0]
    if order not in (0, 1):
        raise Malformed("byte order is neither 0 nor 1")
    prefix = "<" if order == 1 else ">"
    (code,) = struct.unpack(prefix + "I", reader.take(4))
    has_z = bool(code & FLAG_Z)
    has_m = bool(code & FLAG_M)
    has_srid = bool(code & FLAG_SRID)
    base = code & 0x1FFFFFFF
    thousands, kind = divmod(base, 1000)
    if thousands not in ISO_DIMENSIONS:
        raise Malformed("unknown geometry type code")
    if thousands and (has_z or has_m or has_srid):
        raise Malformed("ISO type code with extended flags")
    if thousands:
        has_z, has_m = ISO_DIMENSIONS[thousands]
    name = GEOMETRY_TYPES.get(kind)
    if name is None:
        raise Malformed("unknown geometry type code")
    srid = None
    if has_srid:
        if not outer:
            raise SridOnMember("SRID on a member geometry")
        (srid,) = struct.unpack(prefix + "i", reader.take(4))
    width = 8 * (2 + has_z + has_m)

    def count() -> int:
        (value,) = struct.unpack(prefix + "I", reader.take(4))
        return value

    def points(number: int) -> bytes:
        if number * width > reader.remaining():
            raise Malformed("value ends early")
        return reader.take(number * width)

    def ring() -> None:
        # VOC-011: a linear ring has at least four points and is closed.
        number = count()
        data = points(number)
        if number < 4 or data[:width] != data[-width:]:
            raise Malformed("ring not closed or shorter than four points")

    if name == "point":
        points(1)
    elif name == "linestring":
        if count_points(points, count()) == 1:
            raise Malformed("linestring of one point")
    elif name == "circularstring":
        number = count_points(points, count())
        if number and (number < 3 or number % 2 == 0):
            raise Malformed("circular string without an odd count of at least three points")
    elif name in ("polygon", "triangle"):
        rings = count()
        if rings * 4 > reader.remaining():
            raise Malformed("value ends early")
        if name == "triangle" and rings > 1:
            raise Malformed("triangle with more than one ring")
        for _ in range(rings):
            ring()
    else:
        members = count()
        # Every member has at least a header: bounds the loop by the bytes.
        if members * 5 > reader.remaining():
            raise Malformed("value ends early")
        admitted = MEMBERS[name]
        for _ in range(members):
            member = _geometry(reader, depth + 1, False)
            if admitted is not None and member.type not in admitted:
                raise Malformed("member type not admitted by its container")
            if member.dimensions != DIMENSIONS[(has_z, has_m)]:
                raise Malformed("member dimensions differ from their container")
    return Geometry(name, DIMENSIONS[(has_z, has_m)], srid)


def count_points(points: Any, number: int) -> int:
    points(number)
    return number


def decode_wkb(data: bytes) -> Geometry:
    """Decode one WKB or EWKB value; the whole value must be consumed."""
    reader = _Reader(data)
    geometry = _geometry(reader, 0, True)
    if reader.remaining():
        raise Malformed("bytes after the geometry")
    return geometry


# --- CRS definitions (VOC-005) ------------------------------------------------

_WKT_TOKEN = re.compile(
    r'\s*(?:(?P<open>[\[(])|(?P<close>[\])])|(?P<comma>,)'
    r'|(?P<string>"(?:[^"]|"")*")'
    r'|(?P<number>[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)'
    r'|(?P<word>[A-Za-z_][A-Za-z0-9_]*))'
)


class _Node(NamedTuple):
    keyword: str
    items: list[Any]


def _wkt_tokens(text: str) -> list[tuple[str, str]]:
    tokens = []
    position = 0
    while position < len(text):
        if text[position:].strip() == "":
            break
        match = _WKT_TOKEN.match(text, position)
        if match is None or match.end() == position:
            raise Malformed("unexpected character in WKT")
        kind = match.lastgroup
        assert kind is not None
        tokens.append((kind, match.group(kind)))
        position = match.end()
    return tokens


def parse_wkt(text: str) -> _Node:
    """One bracketed WKT node and nothing after it."""
    tokens = _wkt_tokens(text)
    position = 0

    def node(depth: int) -> _Node:
        nonlocal position
        if depth > MAX_DEPTH:
            raise Malformed("WKT nesting too deep")
        if position + 1 >= len(tokens) or tokens[position][0] != "word" or tokens[position + 1][0] != "open":
            raise Malformed("WKT keyword expected")
        keyword = tokens[position][1]
        opening = tokens[position + 1][1]
        position += 2
        items: list[Any] = []
        while True:
            if position >= len(tokens):
                raise Malformed("unclosed WKT bracket")
            kind, value = tokens[position]
            if kind == "word" and position + 1 < len(tokens) and tokens[position + 1][0] == "open":
                items.append(node(depth + 1))
            elif kind == "string":
                items.append(("string", value[1:-1].replace('""', '"')))
                position += 1
            elif kind in ("number", "word"):
                items.append((kind, value))
                position += 1
            else:
                raise Malformed("WKT value expected")
            if position >= len(tokens):
                raise Malformed("unclosed WKT bracket")
            kind, text_token = tokens[position]
            position += 1
            if kind == "close":
                if {"[": "]", "(": ")"}[opening] != text_token:
                    raise Malformed("WKT brackets of different kinds")
                return _Node(keyword, items)
            if kind != "comma":
                raise Malformed("WKT separator expected")

    root = node(0)
    if position != len(tokens):
        raise Malformed("text after the WKT root")
    return root


def _code(kind: str, value: Any) -> str:
    if kind == "number":
        if not re.fullmatch(r"\+?[0-9]+", str(value)):
            raise Malformed("non-integer numeric authority code")
        return str(int(str(value)))
    return str(value)


def load_projjson(text: str) -> dict[str, Any]:
    """A PROJJSON root object; floats as exact decimals."""
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        if len({key for key, _ in pairs}) != len(pairs):
            raise Malformed("repeated PROJJSON key")
        return dict(pairs)

    def no_constant(name: str) -> Any:
        raise Malformed(f"{name} is not JSON")

    try:
        root = json.loads(
            text, object_pairs_hook=unique, parse_constant=no_constant, parse_float=Decimal
        )
    except json.JSONDecodeError as error:
        raise Malformed("PROJJSON is not JSON") from error
    if not isinstance(root, dict):
        raise Malformed("PROJJSON root is not an object")
    return root


def projjson_identifiers(node: dict[str, Any]) -> list[tuple[str, str]]:
    """The `id` or `ids` of one PROJJSON object."""
    if "id" in node and "ids" in node:
        raise Malformed("PROJJSON object has both id and ids")
    found = [node["id"]] if "id" in node else node.get("ids", [])
    if not isinstance(found, list):
        raise Malformed("PROJJSON ids is not an array")
    pairs = []
    for item in found:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("authority"), str)
            or isinstance(item.get("code"), bool)
            or not isinstance(item.get("code"), (int, str))
        ):
            raise Malformed("PROJJSON identifier is not an authority and a code")
        code = item["code"]
        pairs.append((item["authority"], str(code) if isinstance(code, int) else code))
    return pairs


def wkt_identifiers(node: _Node, keyword: str) -> list[tuple[str, str]]:
    """The identifiers that are direct children of one WKT node."""
    pairs = []
    for item in node.items:
        if isinstance(item, _Node) and item.keyword.upper() == keyword:
            if len(item.items) < 2 or not isinstance(item.items[0], tuple) or item.items[0][0] != "string":
                raise Malformed("authority identifier without an authority name")
            code = item.items[1]
            if not isinstance(code, tuple) or code[0] not in ("string", "number"):
                raise Malformed("authority identifier without a code")
            pairs.append((item.items[0][1], _code(*code)))
    return pairs


WKT1_ROOTS = {"GEOGCS", "PROJCS", "GEOCCS", "VERT_CS", "COMPD_CS", "LOCAL_CS", "FITTED_CS"}
WKT2_ROOTS = {
    "GEOGCRS", "GEOGRAPHICCRS", "GEODCRS", "GEODETICCRS", "PROJCRS", "PROJECTEDCRS",
    "VERTCRS", "VERTICALCRS", "COMPOUNDCRS", "ENGCRS", "ENGINEERINGCRS", "BOUNDCRS",
    "DERIVEDPROJCRS", "TIMECRS", "PARAMETRICCRS",
}


def parse_definition(text: str, definition_format: str) -> _Node:
    """A WKT definition whose root keyword belongs to its declared format."""
    root = parse_wkt(text)
    roots = WKT2_ROOTS if definition_format == "wkt2" else WKT1_ROOTS
    if root.keyword.upper() not in roots:
        raise Malformed("root keyword of another WKT version")
    return root


def definition_identifiers(text: str, definition_format: str) -> list[tuple[str, str]]:
    """The top-level (authority, code) pairs of a CRS definition (VOC-005)."""
    if definition_format == "projjson":
        return projjson_identifiers(load_projjson(text))
    keyword = "ID" if definition_format == "wkt2" else "AUTHORITY"
    return wkt_identifiers(parse_definition(text, definition_format), keyword)


def _same(pair: tuple[str, str], crs_id: str) -> bool:
    authority, _, code = crs_id.partition(":")
    return pair[0].upper() == authority.upper() and pair[1] == code


def definition_contradicts(crs_id: str, text: str, definition_format: str) -> bool:
    """VOC-005: the definition names the authority of `crs_id` and never its
    code. Raises `Malformed` for a definition that is not well-formed."""
    pairs = definition_identifiers(text, definition_format)
    if ":" not in crs_id:
        return False
    authority = crs_id.split(":", 1)[0].upper()
    same_authority = [item for item in pairs if item[0].upper() == authority]
    return bool(same_authority) and not any(_same(item, crs_id) for item in same_authority)


# --- verification before computation (VOC-015) ---------------------------------

class Reference(NamedTuple):
    """The parts VOC-015 requires at least, for one CRS identifier."""

    kind: str
    base: str | None
    ellipsoid: tuple[Decimal, Decimal]
    conversion: tuple[str, dict[str, Decimal]] | None = None


# The reference parts of the identifiers the vectors use (EPSG registry). A
# consumer uses its own CRS knowledge; this table only lets the validator
# derive the verdict a vector states, and an identifier outside it is
# undecidable, as it is for a consumer that does not know it. Every one of
# them has the Greenwich meridian, degrees and metres.
WGS84 = (Decimal("6378137"), Decimal("298.257223563"))
INTERNATIONAL_1924 = (Decimal("6378388"), Decimal("297"))


def transverse_mercator(longitude: str, false_easting: str) -> tuple[str, dict[str, Decimal]]:
    return ("transverse_mercator", {
        "latitude_of_origin": Decimal("0"),
        "central_meridian": Decimal(longitude),
        "scale_factor": Decimal("0.9996"),
        "false_easting": Decimal(false_easting),
        "false_northing": Decimal("0"),
    })


REFERENCE_CRS = {
    "EPSG:4326": Reference("geographic", None, WGS84),
    "EPSG:4265": Reference("geographic", None, INTERNATIONAL_1924),
    "EPSG:3003": Reference("projected", "EPSG:4265", INTERNATIONAL_1924, transverse_mercator("9", "1500000")),
    "EPSG:32632": Reference("projected", "EPSG:4326", WGS84, transverse_mercator("9", "500000")),
    "EPSG:32633": Reference("projected", "EPSG:4326", WGS84, transverse_mercator("15", "500000")),
}
# Parameter spellings of WKT 1, WKT 2 and PROJJSON for the reference methods.
PARAMETER_NAMES = {
    "latitude_of_origin": "latitude_of_origin",
    "latitude of natural origin": "latitude_of_origin",
    "central_meridian": "central_meridian",
    "longitude of natural origin": "central_meridian",
    "scale_factor": "scale_factor",
    "scale factor at natural origin": "scale_factor",
    "false_easting": "false_easting",
    "false easting": "false_easting",
    "false_northing": "false_northing",
    "false northing": "false_northing",
}
METHOD_NAMES = {"transverse_mercator": "transverse_mercator", "transverse mercator": "transverse_mercator"}


class Parts(NamedTuple):
    kind: str
    bases: list[tuple[str, str]]
    ellipsoid: tuple[Decimal, Decimal] | None
    datum_shift: bool
    prime_meridian_zero: bool
    units_decided: bool
    conversion: tuple[str, dict[str, Decimal]] | None


def _children(node: _Node, *keywords: str) -> list[_Node]:
    return [
        item for item in node.items
        if isinstance(item, _Node) and item.keyword.upper() in keywords
    ]


def _descendants(node: _Node, *keywords: str) -> list[_Node]:
    found = []
    for item in node.items:
        if isinstance(item, _Node):
            if item.keyword.upper() in keywords:
                found.append(item)
            found.extend(_descendants(item, *keywords))
    return found


def _anywhere(node: _Node, *keywords: str) -> bool:
    return bool(_descendants(node, *keywords))


def _decimal(item: Any) -> Decimal:
    if not isinstance(item, tuple) or item[0] != "number":
        raise Undecidable("parameter is not a number")
    return Decimal(item[1])


DEGREE = "0.0174532925199433"


def unit_decided(name: str, factor: Decimal) -> bool:
    """A metre, a degree (pi/180 to 15 significant digits) or unity."""
    name = name.lower()
    if name in ("metre", "meter", "unity"):
        return factor == 1
    if name == "degree":
        return f"{factor:.15g}" == DEGREE
    return False


def _wkt_units(root: _Node) -> bool:
    for unit in _descendants(root, "UNIT", "ANGLEUNIT", "LENGTHUNIT", "SCALEUNIT"):
        if len(unit.items) < 2 or not isinstance(unit.items[0], tuple) or unit.items[0][0] != "string":
            raise Undecidable("unit without name and factor")
        if not unit_decided(unit.items[0][1], _decimal(unit.items[1])):
            return False
    return True


def _wkt_ellipsoid(geographic: _Node) -> tuple[Decimal, Decimal] | None:
    for datum in _children(geographic, "DATUM", "GEODETICDATUM", "TRF", "ENSEMBLE"):
        for ellipsoid in _children(datum, "SPHEROID", "ELLIPSOID"):
            if len(ellipsoid.items) < 3:
                raise Undecidable("ellipsoid without its two parameters")
            return _decimal(ellipsoid.items[1]), _decimal(ellipsoid.items[2])
    return None


def _wkt_prime_meridian_zero(geographic: _Node) -> bool:
    meridians = _children(geographic, "PRIMEM", "PRIMEMERIDIAN")
    return all(len(item.items) >= 2 and _decimal(item.items[1]) == 0 for item in meridians)


def _parameters(nodes: list[_Node]) -> dict[str, Decimal]:
    found: dict[str, Decimal] = {}
    for node in nodes:
        if len(node.items) < 2 or not isinstance(node.items[0], tuple):
            raise Undecidable("parameter without name and value")
        name = PARAMETER_NAMES.get(str(node.items[0][1]).lower())
        if name is None or name in found:
            raise Undecidable("parameter outside the reference methods")
        found[name] = _decimal(node.items[1])
    return found


WKT_KINDS = {
    "GEOGCS": "geographic", "GEOGCRS": "geographic", "GEOGRAPHICCRS": "geographic",
    "PROJCS": "projected", "PROJCRS": "projected", "PROJECTEDCRS": "projected",
}


def _wkt_parts(root: _Node, wkt2: bool) -> Parts:
    keyword = root.keyword.upper()
    kind = WKT_KINDS.get(keyword, "other")
    shift = keyword == "BOUNDCRS" or _anywhere(root, "TOWGS84", "BOUNDCRS")
    identifier = "ID" if wkt2 else "AUTHORITY"
    geographic: _Node | None = root
    bases: list[tuple[str, str]] = []
    conversion = None
    if kind == "projected":
        found = _children(root, "BASEGEOGCRS", "BASEGEODCRS") if wkt2 else _children(root, "GEOGCS")
        geographic = found[0] if found else None
        if geographic is not None:
            bases = wkt_identifiers(geographic, identifier)
        if wkt2:
            holders = _children(root, "CONVERSION")
            methods = [method for holder in holders for method in _children(holder, "METHOD", "PROJECTION")]
            parameters = [parameter for holder in holders for parameter in _children(holder, "PARAMETER")]
        else:
            methods = _children(root, "PROJECTION")
            parameters = _children(root, "PARAMETER")
        if len(methods) != 1 or not methods[0].items or not isinstance(methods[0].items[0], tuple):
            raise Undecidable("projection method not readable")
        method = METHOD_NAMES.get(str(methods[0].items[0][1]).lower())
        if method is None:
            raise Undecidable("projection method outside the reference methods")
        conversion = (method, _parameters(parameters))
    if geographic is None:
        raise Undecidable("projected CRS without its base")
    return Parts(
        kind, bases, _wkt_ellipsoid(geographic), shift,
        _wkt_prime_meridian_zero(geographic), _wkt_units(root), conversion,
    )


def _json_number(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise Undecidable("PROJJSON value with a unit or not a number")
    return Decimal(value)


def _projjson_unit(unit: Any) -> bool:
    if isinstance(unit, str):
        return unit.lower() in ("metre", "meter", "degree", "unity")
    if isinstance(unit, dict) and isinstance(unit.get("name"), str):
        return unit_decided(unit["name"], _json_number(unit.get("conversion_factor")))
    raise Undecidable("PROJJSON unit not readable")


def _projjson_parts(root: dict[str, Any]) -> Parts:
    kinds = {"GeographicCRS": "geographic", "ProjectedCRS": "projected"}
    kind = kinds.get(root.get("type"), "other")
    shift = root.get("type") == "BoundCRS"
    geographic = root
    bases: list[tuple[str, str]] = []
    conversion = None
    units = True
    if kind == "projected":
        geographic = root.get("base_crs")
        if not isinstance(geographic, dict):
            raise Undecidable("projected PROJJSON without its base CRS")
        bases = projjson_identifiers(geographic)
        found = root.get("conversion")
        if not isinstance(found, dict) or not isinstance(found.get("method"), dict):
            raise Undecidable("projected PROJJSON without its conversion")
        method = METHOD_NAMES.get(str(found["method"].get("name", "")).lower())
        if method is None or not isinstance(found.get("parameters"), list):
            raise Undecidable("conversion outside the reference methods")
        parameters: dict[str, Decimal] = {}
        for parameter in found["parameters"]:
            if not isinstance(parameter, dict):
                raise Undecidable("parameter not readable")
            name = PARAMETER_NAMES.get(str(parameter.get("name", "")).lower())
            if name is None or name in parameters:
                raise Undecidable("parameter outside the reference methods")
            parameters[name] = _json_number(parameter.get("value"))
            units = units and _projjson_unit(parameter.get("unit", "unity"))
        conversion = (method, parameters)
    datum = geographic.get("datum", geographic.get("datum_ensemble"))
    ellipsoid = None
    if isinstance(datum, dict) and isinstance(datum.get("ellipsoid"), dict):
        found_ellipsoid = datum["ellipsoid"]
        ellipsoid = (
            _json_number(found_ellipsoid.get("semi_major_axis")),
            _json_number(found_ellipsoid.get("inverse_flattening")),
        )
    meridian = geographic.get("prime_meridian")
    zero = meridian is None or (isinstance(meridian, dict) and _json_number(meridian.get("longitude", 0)) == 0)
    return Parts(kind, bases, ellipsoid, shift, zero, units, conversion)


def definition_parts(text: str, definition_format: str) -> Parts:
    if definition_format == "projjson":
        return _projjson_parts(load_projjson(text))
    return _wkt_parts(parse_definition(text, definition_format), definition_format == "wkt2")


def computation_verdict(field: dict[str, Any]) -> Verdict | None:
    """VOC-006 and VOC-015 for one geometry field whose metadata is valid."""
    metadata = field["metadata"]
    definition = metadata.get("plenora.geometry.crs_definition")
    crs_id = metadata.get("plenora.geometry.crs_id")
    if definition is None:
        return None if crs_id in REFERENCE_CRS else Verdict("crs", "VOC-015")
    if crs_id is None:
        # Interpreting a definition completely is beyond the minimum parts:
        # the verdict depends on the consumer's CRS knowledge (VOC-006).
        raise Undecidable("a definition without identifier")
    definition_format = metadata["plenora.geometry.crs_definition_format"]
    if not any(_same(pair, crs_id) for pair in definition_identifiers(definition, definition_format)):
        return Verdict("crs", "VOC-015")
    reference = REFERENCE_CRS.get(crs_id)
    if reference is None:
        return Verdict("crs", "VOC-015")
    try:
        parts = definition_parts(definition, definition_format)
    except Malformed:
        # Well-formed syntax (VOC-005) whose parts cannot be read is undecidable.
        return Verdict("crs", "VOC-015")
    if (
        parts.kind != reference.kind
        or parts.datum_shift
        or parts.ellipsoid != reference.ellipsoid
        or not parts.prime_meridian_zero
        or not parts.units_decided
        or parts.conversion != reference.conversion
    ):
        return Verdict("crs", "VOC-015")
    if parts.bases and not any(_same(pair, reference.base or "") for pair in parts.bases):
        return Verdict("crs", "VOC-015")
    return None


# --- the verdict --------------------------------------------------------------

REQUIRED_GEOMETRY = (
    "plenora.field_id",
    "plenora.geometry.encoding",
    "plenora.geometry.dimensions",
    "plenora.geometry.spatial_semantics",
    "plenora.geometry.precision",
    "plenora.geometry.types_declaration",
    "plenora.geometry.crs_resolution",
)
CLOSED_VALUES = {
    "plenora.geometry.encoding": {"wkb", "ewkb"},
    "plenora.geometry.dimensions": {"xy", "xyz", "xym", "xyzm", "unknown"},
    "plenora.geometry.spatial_semantics": {"geometry", "geography"},
    "plenora.geometry.precision": {"float64", "float32", "native"},
    "plenora.geometry.types_declaration": {"exact", "mixed", "unresolved"},
    "plenora.geometry.crs_resolution": {"resolved", "declared_unresolved", "missing"},
    "plenora.geometry.crs_definition_format": {"wkt", "wkt2", "projjson"},
    "plenora.geometry.axis_order": {
        "lon_lat", "lat_lon", "easting_northing", "northing_easting", "other", "unknown",
    },
}
# Grammars match the whole value (`fullmatch`): `$` would admit a final newline.
DECIMAL = re.compile(r"0|[1-9][0-9]*")
SRID = re.compile(r"0|-?[1-9][0-9]*")
VERSION = re.compile(r"[1-9][0-9]*")
CRS_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*:[^\s:]+")
GEOMETRY_KEYS = set(REQUIRED_GEOMETRY) | set(CLOSED_VALUES) | {
    "plenora.geometry.srid", "plenora.geometry.types", "plenora.geometry.crs_id",
    "plenora.geometry.crs_definition",
}
NATIVE_PREFIX = "plenora.geometry.native."
INTEGER_RANGES = {"int32": 2**31, "int64": 2**63}
VOCABULARY = "VOCABULARY-4"


def is_geometry(field: dict[str, Any]) -> bool:
    return field["metadata"].get("ARROW:extension:name") == "geoarrow.wkb"


def _type_list(text: str | None) -> list[str] | None:
    if text is None:
        return None
    return text.split(",") if text else []


def _vocabulary(fields: list[dict[str, Any]]) -> Verdict | None:
    """Well-formedness of the vocabulary, CRS aside (section 4)."""
    identities = []
    for field in fields:
        metadata = field["metadata"]
        if "plenora.field_id" in metadata:
            if not DECIMAL.fullmatch(metadata["plenora.field_id"]):
                return Verdict("schema", VOCABULARY)
            identities.append(int(metadata["plenora.field_id"]))
        if not is_geometry(field):
            if any(key.startswith("plenora.geometry.") for key in metadata):
                return Verdict("schema", VOCABULARY)
            continue
        if field["type"] not in ("binary", "large_binary"):
            return Verdict("schema", VOCABULARY)
        if any(key not in metadata for key in REQUIRED_GEOMETRY):
            return Verdict("schema", VOCABULARY)
        if any(
            key.startswith("plenora.geometry.") and key not in GEOMETRY_KEYS
            and not key.startswith(NATIVE_PREFIX)
            for key in metadata
        ):
            return Verdict("schema", VOCABULARY)
        for key, values in CLOSED_VALUES.items():
            if key in metadata and metadata[key] not in values:
                return Verdict("schema", VOCABULARY)
        if "plenora.geometry.srid" in metadata:
            srid = metadata["plenora.geometry.srid"]
            if not SRID.fullmatch(srid) or not -(2**31) <= int(srid) < 2**31:
                return Verdict("schema", VOCABULARY)
        declaration = metadata["plenora.geometry.types_declaration"]
        types = _type_list(metadata.get("plenora.geometry.types"))
        if types == []:
            return Verdict("schema", VOCABULARY)
        if declaration == "exact" and not types:
            return Verdict("schema", VOCABULARY)
        if declaration == "unresolved" and types is not None:
            return Verdict("schema", VOCABULARY)
        if types is not None:
            if any(item not in CANONICAL_TYPES for item in types):
                return Verdict("schema", VOCABULARY)
            positions = [CANONICAL_TYPES.index(item) for item in types]
            if positions != sorted(set(positions)):
                return Verdict("schema", VOCABULARY)
        if "plenora.geometry.crs_definition" in metadata and metadata["plenora.geometry.crs_definition"] == "":
            return Verdict("schema", VOCABULARY)
        if "plenora.geometry.crs_id" in metadata and not CRS_ID.fullmatch(metadata["plenora.geometry.crs_id"]):
            return Verdict("schema", VOCABULARY)
    if len(identities) != len(set(identities)):
        return Verdict("schema", VOCABULARY)
    return None


def _crs(fields: list[dict[str, Any]]) -> Verdict | None:
    """The CRS state of every geometry field (section 4, VOC-005)."""
    for field in filter(is_geometry, fields):
        metadata = field["metadata"]
        resolution = metadata["plenora.geometry.crs_resolution"]
        crs_id = metadata.get("plenora.geometry.crs_id")
        definition = metadata.get("plenora.geometry.crs_definition")
        definition_format = metadata.get("plenora.geometry.crs_definition_format")
        axis = metadata.get("plenora.geometry.axis_order")
        if (definition is None) != (definition_format is None):
            return Verdict("crs", VOCABULARY)
        if resolution == "missing":
            if any(value is not None for value in (crs_id, definition, definition_format, axis)):
                return Verdict("crs", VOCABULARY)
            continue
        if crs_id is None and definition is None:
            return Verdict("crs", VOCABULARY)
        if axis is None:
            return Verdict("crs", VOCABULARY)
        if definition is not None:
            try:
                if crs_id is not None and definition_contradicts(crs_id, definition, definition_format):
                    return Verdict("crs", "VOC-005")
                if crs_id is None:
                    definition_identifiers(definition, definition_format)
            except Malformed:
                return Verdict("crs", "VOC-005")
    return None


def _value(field: dict[str, Any], data: bytes) -> Verdict | None:
    metadata = field["metadata"]
    encoding = metadata["plenora.geometry.encoding"]
    try:
        geometry = decode_wkb(data)
    except SridOnMember:
        return Verdict("data_mapping", "VOC-008" if encoding == "wkb" else "VOC-009")
    except Malformed:
        return Verdict("data_mapping", "VOC-011")
    if geometry.srid is not None:
        if encoding == "wkb":
            return Verdict("data_mapping", "VOC-008")
        declared = metadata.get("plenora.geometry.srid")
        if declared is None or int(declared) != geometry.srid:
            return Verdict("crs", "VOC-009")
    types = _type_list(metadata.get("plenora.geometry.types"))
    if types and "unknown" not in types and geometry.type not in types:
        return Verdict("data_mapping", "VOC-011")
    dimensions = metadata["plenora.geometry.dimensions"]
    if dimensions != "unknown" and geometry.dimensions != dimensions:
        return Verdict("data_mapping", "VOC-011")
    return None


def _cell(field: dict[str, Any], value: Any) -> bytes | None:
    """Check that a value fits its Arrow type; return the bytes of a binary."""
    kind = field["type"]
    if value is None:
        if not field["nullable"]:
            raise FixtureError(f"null in non-nullable field {field['name']}")
        return None
    if kind == "bool":
        ok = isinstance(value, bool)
    elif kind in INTEGER_RANGES:
        bound = INTEGER_RANGES[kind]
        ok = isinstance(value, int) and not isinstance(value, bool) and -bound <= value < bound
    elif kind == "float64":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif kind in ("utf8", "large_utf8"):
        ok = isinstance(value, str)
    else:
        ok = isinstance(value, str) and re.fullmatch(r"(?:[0-9a-f]{2})*", value) is not None
        if ok:
            return bytes.fromhex(value)
    if not ok:
        raise FixtureError(f"value does not fit the type of field {field['name']}")
    return None


def verdict(vector: dict[str, Any]) -> Verdict | None:
    """The first rejection a consumer reports, or `None` when it accepts."""
    fields = vector["fields"]
    names = [field["name"] for field in fields]
    if len(names) != len(set(names)):
        raise FixtureError("repeated field name")
    for row in vector["rows"]:
        if set(row) != set(names):
            raise FixtureError("a row does not name exactly the fields")
    cells = [[_cell(field, row[field["name"]]) for field in fields] for row in vector["rows"]]

    version = vector["schema_metadata"].get("plenora.contract.version")
    if version is None or not VERSION.fullmatch(version):
        return Verdict("schema", "ARROW-001")
    if version != "1":
        return Verdict("unsupported", "ARROW-002")
    found = _vocabulary(fields) or _crs(fields)
    if found is not None:
        return found
    for row in cells:
        for field, data in zip(fields, row):
            if data is not None and is_geometry(field):
                found = _value(field, data)
                if found is not None:
                    return found
    return None


def computation_errors(vector: dict[str, Any]) -> list[str]:
    """A valid vector with a CRS definition states the verdict of a consumer
    that computes with the coordinates (VOC-015); one without states none."""
    with_definition = [
        field for field in vector["fields"]
        if is_geometry(field) and "plenora.geometry.crs_definition" in field["metadata"]
    ]
    stated = vector.get("computation")
    if not with_definition:
        return [] if stated is None else ["states a computation verdict without a CRS definition"]
    if stated is None and all(
        "plenora.geometry.crs_id" in field["metadata"] for field in with_definition
    ):
        return ["carries a CRS definition and states no computation verdict"]
    if stated is None:
        return []
    try:
        found = next(filter(None, map(computation_verdict, with_definition)), None)
    except Undecidable:
        return [] if stated is None else ["states a computation verdict the validator cannot decide (VOC-006)"]
    if found is None:
        if stated != "accepted":
            return ["states a computation rejection, the rules accept it"]
        return []
    if stated == "accepted":
        return [f"states computation accepted, but {found.rule} rejects it with {found.category}"]
    if found.rule not in stated["rules"]:
        return [f"computation verdict does not cite {found.rule}, the rule that rejects it"]
    return []


def vector_errors(vector: dict[str, Any]) -> list[str]:
    """Disagreements between a vector and the verdict the rules give."""
    try:
        found = verdict(vector)
    except FixtureError as error:
        return [f"is not a buildable table: {error}"]
    if vector["expect"] == "valid":
        if found is not None:
            return [f"must be accepted, but {found.rule} rejects it with {found.category}"]
        return computation_errors(vector)
    if found is None:
        return ["must be rejected, but every rule accepts it"]
    errors = []
    if vector["category"] != found.category:
        errors.append(f"states category {vector['category']}, the rules give {found.category}")
    if found.rule not in vector["rules"]:
        errors.append(f"does not cite {found.rule}, the rule that rejects it")
    return errors
