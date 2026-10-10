"""Verdicts on Arrow data vectors (Arrow Vocabulary 1.0 section 4 and Arrow Geometry Semantics 1.0).

A vector is a schema fixture with row values. `verdict` derives, from the
rules alone, whether a consumer of the vocabulary accepts it and, when it
does not, the category and the rule that decide the rejection. The validator
compares that verdict with the one the vector states, so a vector cannot
claim a category the rules do not give.

The checks run in a fixed order: the schema contract version (ARROW-001,
ARROW-002), the well-formedness of the vocabulary (section 4), the CRS state
(section 4, GEO-005), then each geometry value in row order and, within a
row, in field order (GEO-008, GEO-009, GEO-011). The first failure is the
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
    """An SRID flag on a member geometry: GEO-008 under `wkb`, GEO-009 under
    `ewkb`."""


class Undecidable(Malformed):
    """Well-formed CRS definition whose parts GEO-015 cannot decide."""


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
        # GEO-011: a linear ring has at least four points and is closed.
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


# --- CRS definitions (GEO-005) ------------------------------------------------

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
    """The top-level (authority, code) pairs of a CRS definition (GEO-005)."""
    if definition_format == "projjson":
        return projjson_identifiers(load_projjson(text))
    keyword = "ID" if definition_format == "wkt2" else "AUTHORITY"
    return wkt_identifiers(parse_definition(text, definition_format), keyword)


def _same(pair: tuple[str, str], crs_id: str) -> bool:
    authority, _, code = crs_id.partition(":")
    return pair[0].upper() == authority.upper() and pair[1] == code


def definition_contradicts(crs_id: str, text: str, definition_format: str) -> bool:
    """GEO-005: the definition names the authority of `crs_id` and never its
    code. Raises `Malformed` for a definition that is not well-formed."""
    pairs = definition_identifiers(text, definition_format)
    if ":" not in crs_id:
        return False
    authority = crs_id.split(":", 1)[0].upper()
    same_authority = [item for item in pairs if item[0].upper() == authority]
    return bool(same_authority) and not any(_same(item, crs_id) for item in same_authority)


# --- verification before computation (GEO-015, GEO-017) ---------------------------

class Reference(NamedTuple):
    """The parts GEO-015 compares, for one CRS identifier."""

    kind: str
    base: str | None
    datum: str
    ellipsoid: tuple[Decimal, Decimal]
    conversion: tuple[str, dict[str, Decimal]] | None = None


# The reference parts of the identifiers the vectors use (EPSG registry). A
# component uses its own CRS knowledge; this table only lets the validator
# derive the verdict a vector states, and an identifier outside it is
# undecidable, as it is for a component that does not know it. Every one of
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
    "EPSG:4326": Reference("geographic", None, "EPSG:6326", WGS84),
    "EPSG:4265": Reference("geographic", None, "EPSG:6265", INTERNATIONAL_1924),
    "EPSG:3003": Reference("projected", "EPSG:4265", "EPSG:6265", INTERNATIONAL_1924,
                           transverse_mercator("9", "1500000")),
    "EPSG:32632": Reference("projected", "EPSG:4326", "EPSG:6326", WGS84, transverse_mercator("9", "500000")),
    "EPSG:32633": Reference("projected", "EPSG:4326", "EPSG:6326", WGS84, transverse_mercator("15", "500000")),
}
# GEO-017: the closed alias lists, compared ASCII case-insensitively.
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
PARAMETER_QUANTITY = {
    "latitude_of_origin": "angle",
    "central_meridian": "angle",
    "scale_factor": "scale",
    "false_easting": "length",
    "false_northing": "length",
}
METHOD_NAMES = {"transverse_mercator": "transverse_mercator", "transverse mercator": "transverse_mercator"}
# GEO-017: the decided units. The degree has two exact spellings.
UNIT_NAMES = {"angle": {"degree"}, "length": {"metre", "meter"}, "scale": {"unity"}}
DEGREE_FACTORS = (Decimal("0.0174532925199433"), Decimal("0.017453292519943295"))
WKT2_UNIT_QUANTITY = {"ANGLEUNIT": "angle", "LENGTHUNIT": "length", "SCALEUNIT": "scale"}


def unit_decided(name: str, factor: Decimal, quantity: str) -> bool:
    """A unit of the subset for the quantity it measures (GEO-017)."""
    if name.lower() not in UNIT_NAMES[quantity]:
        return False
    if quantity == "angle":
        return any(factor == degree for degree in DEGREE_FACTORS)
    return factor == 1


def _require_unit(name: Any, factor: Any, quantity: str) -> None:
    if not isinstance(name, str) or not isinstance(factor, Decimal) or not unit_decided(name, factor, quantity):
        raise Undecidable(f"unit not decided for {quantity}")


class Parts(NamedTuple):
    kind: str
    bases: list[tuple[str, str]]
    datums: list[tuple[str, str]]
    ellipsoid: tuple[Decimal, Decimal] | None
    datum_shift: bool
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
        raise Undecidable("not a number")
    return Decimal(item[1])


def _one(nodes: list[_Node], what: str) -> _Node:
    if len(nodes) != 1:
        raise Undecidable(f"{what} missing or repeated")
    return nodes[0]


def _wkt_unit(node: _Node, quantity: str) -> None:
    if len(node.items) < 2 or not isinstance(node.items[0], tuple) or node.items[0][0] != "string":
        raise Undecidable("unit without name and factor")
    _require_unit(node.items[0][1], _decimal(node.items[1]), quantity)


def _name(node: _Node) -> str:
    if not node.items or not isinstance(node.items[0], tuple) or node.items[0][0] != "string":
        raise Undecidable("element without a name")
    return node.items[0][1].lower()


def _ellipsoid(datum: _Node, wkt2: bool) -> tuple[Decimal, Decimal]:
    ellipsoid = _one(_children(datum, "SPHEROID", "ELLIPSOID"), "ellipsoid")
    if len(ellipsoid.items) < 3:
        raise Undecidable("ellipsoid without its two parameters")
    if wkt2:
        for unit in _children(ellipsoid, "LENGTHUNIT"):
            _wkt_unit(unit, "length")
        if _children(ellipsoid, "UNIT", "ANGLEUNIT", "SCALEUNIT"):
            raise Undecidable("ellipsoid unit of another quantity")
    return _decimal(ellipsoid.items[1]), _decimal(ellipsoid.items[2])


def _prime_meridian_zero(geographic: _Node, wkt2: bool) -> None:
    meridians = _children(geographic, "PRIMEM", "PRIMEMERIDIAN")
    if not meridians and not wkt2:
        raise Undecidable("WKT 1 without its prime meridian")
    for meridian in meridians:
        if len(meridian.items) < 2 or _decimal(meridian.items[1]) != 0:
            raise Undecidable("prime meridian other than Greenwich")
        for unit in _children(meridian, "ANGLEUNIT"):
            _wkt_unit(unit, "angle")
        if _children(meridian, "UNIT", "LENGTHUNIT", "SCALEUNIT"):
            raise Undecidable("prime meridian unit of another quantity")


def _wkt_conversion(holder: _Node, wkt2: bool) -> tuple[str, dict[str, Decimal]]:
    method = _one(_children(holder, "METHOD", "PROJECTION"), "projection method")
    name = METHOD_NAMES.get(_name(method))
    if name is None:
        raise Undecidable("method outside the subset")
    parameters: dict[str, Decimal] = {}
    for parameter in _children(holder, "PARAMETER"):
        key = PARAMETER_NAMES.get(_name(parameter))
        if key is None or key in parameters or len(parameter.items) < 2:
            raise Undecidable("parameter outside the subset or repeated")
        if wkt2:
            units = [item for item in parameter.items[2:] if isinstance(item, _Node)]
            unit = _one(units, "parameter unit")
            if WKT2_UNIT_QUANTITY.get(unit.keyword.upper()) != PARAMETER_QUANTITY[key]:
                raise Undecidable("parameter unit of another quantity")
            _wkt_unit(unit, PARAMETER_QUANTITY[key])
        parameters[key] = _decimal(parameter.items[1])
    return name, parameters


def _wkt2_cs_unit(crs: _Node, quantity: str) -> None:
    keyword = "ANGLEUNIT" if quantity == "angle" else "LENGTHUNIT"
    if _children(crs, "UNIT"):
        raise Undecidable("generic WKT 2 unit")
    direct = _children(crs, keyword)
    axes = _children(crs, "AXIS")
    if direct:
        _wkt_unit(_one(direct, "coordinate system unit"), quantity)
    elif axes and all(_children(axis, keyword) for axis in axes):
        for axis in axes:
            _wkt_unit(_one(_children(axis, keyword), "axis unit"), quantity)
    else:
        raise Undecidable("coordinate system without its unit")
    other = {"ANGLEUNIT": "LENGTHUNIT", "LENGTHUNIT": "ANGLEUNIT"}[keyword]
    if _children(crs, other) or any(_children(axis, other) for axis in axes):
        raise Undecidable("coordinate system unit of another quantity")


WKT_KINDS = {
    "GEOGCS": "geographic", "GEOGCRS": "geographic", "GEOGRAPHICCRS": "geographic",
    "PROJCS": "projected", "PROJCRS": "projected", "PROJECTEDCRS": "projected",
}


def _wkt_parts(root: _Node, wkt2: bool) -> Parts:
    keyword = root.keyword.upper()
    kind = WKT_KINDS.get(keyword, "other")
    shift = keyword == "BOUNDCRS" or _anywhere(root, "TOWGS84", "BOUNDCRS", "ABRIDGEDTRANSFORMATION")
    if kind == "other" or shift:
        return Parts(kind, [], [], None, shift, None)
    identifier = "ID" if wkt2 else "AUTHORITY"
    bases: list[tuple[str, str]] = []
    conversion = None
    if kind == "projected":
        found = _children(root, "BASEGEOGCRS", "BASEGEODCRS") if wkt2 else _children(root, "GEOGCS")
        geographic = _one(found, "base CRS")
        bases = wkt_identifiers(geographic, identifier)
        if wkt2:
            conversion = _wkt_conversion(_one(_children(root, "CONVERSION"), "conversion"), True)
            _wkt2_cs_unit(root, "length")
            for unit in _children(geographic, "ANGLEUNIT"):
                _wkt_unit(unit, "angle")
        else:
            conversion = _wkt_conversion(root, False)
            _wkt_unit(_one(_children(root, "UNIT"), "linear unit"), "length")
            _wkt_unit(_one(_children(geographic, "UNIT"), "angular unit"), "angle")
    else:
        geographic = root
        if wkt2:
            _wkt2_cs_unit(root, "angle")
        else:
            _wkt_unit(_one(_children(root, "UNIT"), "angular unit"), "angle")
    datum = _one(_children(geographic, "DATUM", "GEODETICDATUM", "TRF", "ENSEMBLE"), "datum")
    _prime_meridian_zero(geographic, wkt2)
    return Parts(
        kind, bases, wkt_identifiers(datum, identifier), _ellipsoid(datum, wkt2), False, conversion,
    )


def _json_value(value: Any, quantity: str) -> Decimal:
    """A PROJJSON number, bare (in the default unit) or with its unit."""
    if isinstance(value, dict):
        _projjson_unit(value.get("unit"), quantity)
        value = value.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise Undecidable("PROJJSON value not a number")
    return Decimal(value)


def _projjson_unit(unit: Any, quantity: str) -> None:
    if isinstance(unit, str):
        if unit.lower() not in UNIT_NAMES[quantity]:
            raise Undecidable("PROJJSON unit not decided")
        return
    if isinstance(unit, dict):
        factor = unit.get("conversion_factor")
        if isinstance(factor, int) and not isinstance(factor, bool):
            factor = Decimal(factor)
        _require_unit(unit.get("name"), factor, quantity)
        return
    raise Undecidable("PROJJSON unit missing")


def _projjson_parts(root: dict[str, Any]) -> Parts:
    kinds = {"GeographicCRS": "geographic", "ProjectedCRS": "projected"}
    kind = kinds.get(root.get("type"), "other")
    if root.get("type") == "BoundCRS" or kind == "other":
        return Parts(kind, [], [], None, root.get("type") == "BoundCRS", None)
    geographic = root
    bases: list[tuple[str, str]] = []
    conversion = None
    quantity = "angle"
    if kind == "projected":
        quantity = "length"
        geographic = root.get("base_crs")
        if not isinstance(geographic, dict):
            raise Undecidable("projected PROJJSON without its base CRS")
        bases = projjson_identifiers(geographic)
        found = root.get("conversion")
        if not isinstance(found, dict) or not isinstance(found.get("method"), dict):
            raise Undecidable("projected PROJJSON without its conversion")
        method = METHOD_NAMES.get(str(found["method"].get("name", "")).lower())
        if method is None or not isinstance(found.get("parameters"), list):
            raise Undecidable("conversion outside the subset")
        parameters: dict[str, Decimal] = {}
        for parameter in found["parameters"]:
            if not isinstance(parameter, dict):
                raise Undecidable("parameter not readable")
            name = PARAMETER_NAMES.get(str(parameter.get("name", "")).lower())
            if name is None or name in parameters:
                raise Undecidable("parameter outside the subset or repeated")
            _projjson_unit(parameter.get("unit"), PARAMETER_QUANTITY[name])
            parameters[name] = _json_value(parameter.get("value"), PARAMETER_QUANTITY[name])
        conversion = (method, parameters)
    system = root.get("coordinate_system")
    if not isinstance(system, dict) or not isinstance(system.get("axis"), list) or not system["axis"]:
        raise Undecidable("PROJJSON without its coordinate system")
    for axis in system["axis"]:
        if not isinstance(axis, dict):
            raise Undecidable("axis not readable")
        _projjson_unit(axis.get("unit"), quantity)
    datum = geographic.get("datum", geographic.get("datum_ensemble"))
    if not isinstance(datum, dict) or not isinstance(datum.get("ellipsoid"), dict):
        raise Undecidable("PROJJSON without its datum and ellipsoid")
    ellipsoid = datum["ellipsoid"]
    if "inverse_flattening" not in ellipsoid:
        raise Undecidable("ellipsoid without inverse flattening")
    axes = (
        _json_value(ellipsoid.get("semi_major_axis"), "length"),
        _json_value(ellipsoid.get("inverse_flattening"), "scale"),
    )
    meridian = geographic.get("prime_meridian")
    if meridian is not None:
        if not isinstance(meridian, dict) or _json_value(meridian.get("longitude", 0), "angle") != 0:
            raise Undecidable("prime meridian other than Greenwich")
    return Parts(kind, bases, projjson_identifiers(datum), axes, False, conversion)


def definition_parts(text: str, definition_format: str) -> Parts:
    if definition_format == "projjson":
        return _projjson_parts(load_projjson(text))
    return _wkt_parts(parse_definition(text, definition_format), definition_format == "wkt2")


def computation_verdict(field: dict[str, Any]) -> Verdict | None:
    """GEO-006 and GEO-015 for one geometry field whose metadata is valid."""
    metadata = field["metadata"]
    definition = metadata.get("plenora.geometry.crs_definition")
    crs_id = metadata.get("plenora.geometry.crs_id")
    if definition is None:
        return None if crs_id in REFERENCE_CRS else Verdict("crs", "GEO-015")
    if crs_id is None:
        # Interpreting a definition completely is beyond the subset: the
        # verdict depends on the component's CRS knowledge (GEO-006).
        raise Undecidable("a definition without identifier")
    definition_format = metadata["plenora.geometry.crs_definition_format"]
    if not any(_same(pair, crs_id) for pair in definition_identifiers(definition, definition_format)):
        return Verdict("crs", "GEO-015")
    reference = REFERENCE_CRS.get(crs_id)
    if reference is None:
        return Verdict("crs", "GEO-015")
    try:
        parts = definition_parts(definition, definition_format)
    except Malformed:
        # Well-formed syntax (GEO-005) with an undecidable part (GEO-017).
        return Verdict("crs", "GEO-015")
    if (
        parts.kind != reference.kind
        or parts.datum_shift
        or parts.ellipsoid != reference.ellipsoid
        or parts.conversion != reference.conversion
    ):
        return Verdict("crs", "GEO-015")
    if parts.bases and not any(_same(pair, reference.base or "") for pair in parts.bases):
        return Verdict("crs", "GEO-015")
    if parts.datums and not any(_same(pair, reference.datum) for pair in parts.datums):
        return Verdict("crs", "GEO-015")
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
            return Verdict("schema", "GEO-016")
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
            return Verdict("schema", "GEO-016")
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
            return Verdict("schema", "GEO-016")
    if len(identities) != len(set(identities)):
        return Verdict("schema", VOCABULARY)
    return None


def _crs(fields: list[dict[str, Any]]) -> Verdict | None:
    """The CRS state of every geometry field (section 4, GEO-005)."""
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
                    return Verdict("crs", "GEO-005")
                if crs_id is None:
                    definition_identifiers(definition, definition_format)
            except Malformed:
                return Verdict("crs", "GEO-005")
    return None


def _value(field: dict[str, Any], data: bytes) -> Verdict | None:
    metadata = field["metadata"]
    encoding = metadata["plenora.geometry.encoding"]
    try:
        geometry = decode_wkb(data)
    except SridOnMember:
        return Verdict("data_mapping", "GEO-008" if encoding == "wkb" else "GEO-009")
    except Malformed:
        return Verdict("data_mapping", "GEO-011")
    if geometry.srid is not None:
        if encoding == "wkb":
            return Verdict("data_mapping", "GEO-008")
        declared = metadata.get("plenora.geometry.srid")
        if declared is None or int(declared) != geometry.srid:
            return Verdict("crs", "GEO-009")
    types = _type_list(metadata.get("plenora.geometry.types"))
    if types and "unknown" not in types and geometry.type not in types:
        return Verdict("data_mapping", "GEO-011")
    dimensions = metadata["plenora.geometry.dimensions"]
    if dimensions != "unknown" and geometry.dimensions != dimensions:
        return Verdict("data_mapping", "GEO-011")
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
    that computes with the coordinates (GEO-015); one without states none."""
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
        return [] if stated is None else ["states a computation verdict the validator cannot decide (GEO-006)"]
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
