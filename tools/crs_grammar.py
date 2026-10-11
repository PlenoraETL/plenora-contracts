"""The closed grammar of a verifiable CRS definition (Arrow Geometry Semantics
1.0, GEO-019).

A definition is verifiable only when it is made entirely of the nodes and
members listed here; anything else (a dynamic frame, a frame epoch, a datum
ensemble other than a reference one, a usage holding something else than its
listed parts, a member a future version of a format adds) makes it
undecidable. The lists are the normative tables of GEO-019: the validator and
the specification state the same sets.

Usage metadata (`USAGE`, `SCOPE`, `AREA`, `BBOX`, `REMARK` and their
PROJJSON equivalents) is ignorable: it never enters the comparison, but its
content has a closed grammar of its own, so an unknown node inside it is
undecidable too.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, NamedTuple


class Node(NamedTuple):
    """What a WKT node admits: at most `scalars` scalar items (exactly the
    kinds in `kinds`, when stated), and child nodes among `children`, each
    once unless it is in `repeated`."""

    scalars: int
    children: frozenset[str]
    repeated: frozenset[str] = frozenset()
    kinds: tuple[str, ...] | None = None


def node(scalars: int, *children: str, repeated: tuple[str, ...] = (),
         kinds: tuple[str, ...] | None = None) -> Node:
    return Node(scalars, frozenset(children), frozenset(repeated), kinds)


def text(*children: str, repeated: tuple[str, ...] = ()) -> Node:
    """A node with exactly one quoted text."""
    return node(1, *children, repeated=repeated, kinds=("string",))


def numbers(count: int) -> Node:
    """A node with exactly `count` numbers and no child."""
    return node(count, kinds=("number",) * count)


# WKT 1 (GEOGCS, PROJCS and their parts).
WKT1 = {
    "GEOGCS": node(1, "DATUM", "PRIMEM", "UNIT", "AXIS", "AUTHORITY", repeated=("AXIS",)),
    "PROJCS": node(1, "GEOGCS", "PROJECTION", "PARAMETER", "UNIT", "AXIS", "AUTHORITY",
                   repeated=("PARAMETER", "AXIS")),
    "DATUM": node(1, "SPHEROID", "AUTHORITY"),
    "SPHEROID": node(3, "AUTHORITY"),
    "PRIMEM": node(2, "AUTHORITY"),
    "UNIT": node(2, "AUTHORITY"),
    "AXIS": node(2),
    "PROJECTION": node(1, "AUTHORITY"),
    "PARAMETER": node(2),
    "AUTHORITY": node(2),
}
# The ignorable usage metadata a WKT 2 CRS may carry (GEO-019).
USAGE_CHILDREN = ("USAGE", "SCOPE", "AREA", "BBOX", "REMARK")
# WKT 2 (GEOGCRS, PROJCRS and their parts).
WKT2 = {
    "GEOGCRS": node(1, "DATUM", "ENSEMBLE", "PRIMEM", "CS", "AXIS", "ANGLEUNIT", "ID", *USAGE_CHILDREN,
                    repeated=("AXIS", "ID", "USAGE")),
    "PROJCRS": node(1, "BASEGEOGCRS", "CONVERSION", "CS", "AXIS", "LENGTHUNIT", "ID", *USAGE_CHILDREN,
                    repeated=("AXIS", "ID", "USAGE")),
    "BASEGEOGCRS": node(1, "DATUM", "ENSEMBLE", "PRIMEM", "ANGLEUNIT", "ID", repeated=("ID",)),
    "DATUM": node(1, "ELLIPSOID", "ID", repeated=("ID",)),
    "ENSEMBLE": text("MEMBER", "ELLIPSOID", "ENSEMBLEACCURACY", "ID", repeated=("MEMBER", "ID")),
    "MEMBER": text("ID", repeated=("ID",)),
    "ENSEMBLEACCURACY": numbers(1),
    "ELLIPSOID": node(3, "LENGTHUNIT", "ID", repeated=("ID",)),
    "PRIMEM": node(2, "ANGLEUNIT", "ID", repeated=("ID",)),
    "CS": node(2),
    "AXIS": node(2, "ORDER", "ANGLEUNIT", "LENGTHUNIT"),
    "ORDER": numbers(1),
    "CONVERSION": node(1, "METHOD", "PARAMETER", "ID", repeated=("PARAMETER", "ID")),
    "METHOD": node(1, "ID", repeated=("ID",)),
    "PARAMETER": node(2, "ANGLEUNIT", "LENGTHUNIT", "SCALEUNIT", "ID", repeated=("ID",)),
    "ANGLEUNIT": node(2, "ID", repeated=("ID",)),
    "LENGTHUNIT": node(2, "ID", repeated=("ID",)),
    "SCALEUNIT": node(2, "ID", repeated=("ID",)),
    "ID": node(2),
    "USAGE": node(0, "SCOPE", "AREA", "BBOX", "ID", repeated=("ID",)),
    "SCOPE": text(),
    "AREA": text(),
    "BBOX": numbers(4),
    "REMARK": text(),
}
WKT_ROOTS = {"wkt": {"GEOGCS", "PROJCS"}, "wkt2": {"GEOGCRS", "PROJCRS"}}

# PROJJSON: the members each object admits, and the objects its members hold.
ID_MEMBERS = {"authority", "code"}
UNIT_MEMBERS = {"type", "name", "conversion_factor"}
BBOX_MEMBERS = {"south_latitude", "west_longitude", "north_latitude", "east_longitude"}
USAGE_MEMBERS = {"scope", "area", "bbox", "usages", "remarks"}
PROJJSON = {
    "GeographicCRS": {"$schema", "type", "name", "datum", "datum_ensemble", "coordinate_system", "id", "ids",
                      *USAGE_MEMBERS},
    "ProjectedCRS": {"$schema", "type", "name", "base_crs", "conversion", "coordinate_system", "id", "ids",
                     *USAGE_MEMBERS},
    "base_crs": {"type", "name", "datum", "datum_ensemble", "coordinate_system", "id", "ids"},
    "datum": {"type", "name", "ellipsoid", "prime_meridian", "id", "ids"},
    "datum_ensemble": {"type", "name", "members", "ellipsoid", "accuracy", "id", "ids"},
    "member": {"name", "id", "ids"},
    "ellipsoid": {"name", "semi_major_axis", "inverse_flattening", "id", "ids"},
    "prime_meridian": {"name", "longitude", "id", "ids"},
    "coordinate_system": {"subtype", "axis"},
    "axis": {"name", "abbreviation", "direction", "unit"},
    "conversion": {"name", "method", "parameters", "id", "ids"},
    "method": {"name", "id", "ids"},
    "parameter": {"name", "value", "unit", "id", "ids"},
    "value": {"value", "unit"},
    "usage": {"scope", "area", "bbox", "id", "ids"},
}
PROJJSON_TYPES = {
    "base_crs": {"GeographicCRS"},
    "datum": {"GeodeticReferenceFrame"},
    "datum_ensemble": {"DatumEnsemble"},
}


class Ensemble(NamedTuple):
    """A reference datum ensemble: its name, identifier, members (name and
    identifier, in order) and accuracy, as the EPSG registry states them."""

    name: str
    identifier: tuple[str, str]
    members: tuple[tuple[str, tuple[str, str]], ...]
    accuracy: Decimal


# GEO-019: the only datum ensembles a verifiable definition may hold. The
# members are those of EPSG v12.013 (PROJ 9.6.2); a registry that adds or
# removes a member produces another ensemble, which is undecidable until this
# table follows it.
REFERENCE_ENSEMBLES = (
    Ensemble(
        "World Geodetic System 1984 ensemble",
        ("EPSG", "6326"),
        (
            ("World Geodetic System 1984 (Transit)", ("EPSG", "1166")),
            ("World Geodetic System 1984 (G730)", ("EPSG", "1152")),
            ("World Geodetic System 1984 (G873)", ("EPSG", "1153")),
            ("World Geodetic System 1984 (G1150)", ("EPSG", "1154")),
            ("World Geodetic System 1984 (G1674)", ("EPSG", "1155")),
            ("World Geodetic System 1984 (G1762)", ("EPSG", "1156")),
            ("World Geodetic System 1984 (G2139)", ("EPSG", "1309")),
            ("World Geodetic System 1984 (G2296)", ("EPSG", "1383")),
        ),
        Decimal("2.0"),
    ),
)

_DECIMAL = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class Outside(Exception):
    """A node or member outside the closed grammar."""


def _code_text(kind: str, value: str) -> str:
    if kind == "number":
        if not re.fullmatch(r"\+?[0-9]+", value):
            raise Outside("non-integer identifier code")
        return str(int(value))
    return value


def _same_identifier(found: tuple[str, str], expected: tuple[str, str]) -> bool:
    return found[0].upper() == expected[0].upper() and found[1] == expected[1]


def _match_ensemble(name: Any, members: list[tuple[Any, list[tuple[str, str]]]],
                    accuracy: Any, identifiers: list[tuple[str, str]]) -> Ensemble:
    """The reference ensemble these parts are identical to, or `Outside`."""
    if not isinstance(accuracy, str) or not _DECIMAL.fullmatch(accuracy):
        raise Outside("ensemble accuracy missing or not a number")
    for reference in REFERENCE_ENSEMBLES:
        if (
            isinstance(name, str)
            and name.lower() == reference.name.lower()
            and len(members) == len(reference.members)
            and all(
                isinstance(found, str) and found.lower() == expected.lower()
                and all(_same_identifier(pair, expected_id) for pair in pairs)
                for (found, pairs), (expected, expected_id) in zip(members, reference.members)
            )
            and Decimal(accuracy) == reference.accuracy
            and all(_same_identifier(pair, reference.identifier) for pair in identifiers)
        ):
            return reference
    raise Outside("datum ensemble other than a reference one")


def _wkt_ids(current: Any) -> list[tuple[str, str]]:
    pairs = []
    for item in current.items:
        if hasattr(item, "keyword") and item.keyword.upper() == "ID":
            if (
                len(item.items) != 2
                or not isinstance(item.items[0], tuple) or item.items[0][0] != "string"
                or not isinstance(item.items[1], tuple) or item.items[1][0] not in ("string", "number")
            ):
                raise Outside("identifier not an authority and a code")
            pairs.append((item.items[0][1], _code_text(*item.items[1])))
    return pairs


def _wkt_children(current: Any, keyword: str) -> list[Any]:
    return [item for item in current.items if hasattr(item, "keyword") and item.keyword.upper() == keyword]


def wkt_ensemble(current: Any) -> Ensemble:
    """The reference ensemble a WKT 2 `ENSEMBLE` node is identical to."""
    members = [(member.items[0][1], _wkt_ids(member)) for member in _wkt_children(current, "MEMBER")]
    accuracies = _wkt_children(current, "ENSEMBLEACCURACY")
    accuracy = accuracies[0].items[0][1] if len(accuracies) == 1 else None
    return _match_ensemble(current.items[0][1], members, accuracy, _wkt_ids(current))


def _projjson_ids(holder: dict[str, Any]) -> list[tuple[str, str]]:
    if "id" in holder and "ids" in holder:
        raise Outside("both id and ids")
    found = [holder["id"]] if "id" in holder else holder.get("ids", [])
    if not isinstance(found, list):
        raise Outside("ids is not an array")
    pairs = []
    for item in found:
        if not isinstance(item, dict) or set(item) - ID_MEMBERS:
            raise Outside("identifier member outside the grammar")
        code = item.get("code")
        if not isinstance(item.get("authority"), str) or isinstance(code, bool) or not isinstance(code, (int, str)):
            raise Outside("identifier not an authority and a code")
        pairs.append((item["authority"], str(code)))
    return pairs


def projjson_ensemble(value: dict[str, Any]) -> Ensemble:
    """The reference ensemble a PROJJSON `datum_ensemble` is identical to."""
    members = value.get("members")
    if not isinstance(members, list):
        raise Outside("ensemble members missing")
    for member in members:
        if not isinstance(member, dict):
            raise Outside("ensemble member not an object")
    return _match_ensemble(
        value.get("name"),
        [(member.get("name"), _projjson_ids(member)) for member in members],
        value.get("accuracy"),
        _projjson_ids(value),
    )


def check_wkt(root: Any, definition_format: str) -> None:
    """Raise `Outside` unless every node of the parsed WKT is admitted."""
    grammar = WKT2 if definition_format == "wkt2" else WKT1
    if root.keyword.upper() not in WKT_ROOTS[definition_format]:
        raise Outside("root keyword outside the grammar")

    def visit(current: Any) -> None:
        rule = grammar.get(current.keyword.upper())
        if rule is None:
            raise Outside("keyword outside the grammar")
        scalars = [item for item in current.items if not hasattr(item, "keyword")]
        if len(scalars) > rule.scalars:
            raise Outside("too many values")
        if rule.kinds is not None and tuple(kind for kind, _ in scalars) != rule.kinds:
            raise Outside("values of another kind")
        seen: dict[str, int] = {}
        for item in current.items:
            if not hasattr(item, "keyword"):
                continue
            keyword = item.keyword.upper()
            if keyword not in rule.children:
                raise Outside("child outside the grammar")
            seen[keyword] = seen.get(keyword, 0) + 1
            if seen[keyword] > 1 and keyword not in rule.repeated:
                raise Outside("child repeated")
            visit(item)
        # An axis order, when stated, is the position of every axis: it
        # never reorders the axes the definition lists.
        axes = _wkt_children(current, "AXIS")
        orders = [_wkt_children(axis, "ORDER") for axis in axes]
        if any(orders):
            for position, found in enumerate(orders, start=1):
                if not found or _code_text(*found[0].items[0]) != str(position):
                    raise Outside("axis order other than the listed one")
        if current.keyword.upper() == "ENSEMBLE":
            wkt_ensemble(current)

    visit(root)


def check_projjson(root: Any) -> None:
    """Raise `Outside` unless every object and member is admitted."""

    def unit(value: Any) -> None:
        if isinstance(value, dict) and set(value) - UNIT_MEMBERS:
            raise Outside("unit member outside the grammar")

    def number(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) - PROJJSON["value"]:
                raise Outside("value member outside the grammar")
            unit(value.get("unit"))

    def usage(value: dict[str, Any]) -> None:
        for member in ("scope", "area", "remarks"):
            if member in value and not isinstance(value[member], str):
                raise Outside("usage text not a string")
        if "bbox" in value:
            box = value["bbox"]
            if not isinstance(box, dict) or set(box) != BBOX_MEMBERS or any(
                isinstance(item, bool) or not isinstance(item, (int, Decimal)) for item in box.values()
            ):
                raise Outside("bounding box outside the grammar")
        if "usages" in value:
            if not isinstance(value["usages"], list):
                raise Outside("usages is not an array")
            for item in value["usages"]:
                visit(item, "usage")

    def visit(value: Any, kind: str) -> None:
        if not isinstance(value, dict):
            raise Outside("object expected")
        if set(value) - PROJJSON[kind]:
            raise Outside("member outside the grammar")
        if kind in PROJJSON_TYPES and "type" in value and value["type"] not in PROJJSON_TYPES[kind]:
            raise Outside("object type outside the grammar")
        if "datum" in value and "datum_ensemble" in value:
            raise Outside("both a datum and a datum ensemble")
        _projjson_ids(value)
        usage(value)
        for member, child in (("datum", "datum"), ("datum_ensemble", "datum_ensemble"),
                              ("ellipsoid", "ellipsoid"), ("prime_meridian", "prime_meridian"),
                              ("coordinate_system", "coordinate_system"), ("conversion", "conversion"),
                              ("method", "method"), ("base_crs", "base_crs")):
            if member in value:
                visit(value[member], child)
        for member in ("semi_major_axis", "inverse_flattening", "longitude", "value"):
            if member in value:
                number(value[member])
        if "unit" in value:
            unit(value["unit"])
        for member, child in (("axis", "axis"), ("parameters", "parameter"), ("members", "member")):
            if member in value:
                if not isinstance(value[member], list):
                    raise Outside("array expected")
                for item in value[member]:
                    visit(item, child)
        if kind == "datum_ensemble":
            projjson_ensemble(value)

    kind = root.get("type") if isinstance(root, dict) else None
    if kind not in ("GeographicCRS", "ProjectedCRS"):
        raise Outside("root type outside the grammar")
    visit(root, kind)
