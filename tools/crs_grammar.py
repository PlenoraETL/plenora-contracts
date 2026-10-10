"""The closed grammar of a verifiable CRS definition (Arrow Geometry Semantics
1.0, GEO-019).

A definition is verifiable only when it is made entirely of the nodes and
members listed here; anything else (a dynamic frame, a frame epoch, a datum
ensemble, a usage, a remark, a unit on an axis, a member a future version of
a format adds) makes it undecidable. The lists are the normative tables of
GEO-019: the validator and the specification state the same sets.
"""

from __future__ import annotations

from typing import Any, NamedTuple


class Node(NamedTuple):
    """What a WKT node admits: its scalar items, at most `scalars` of them,
    and child nodes among `children`, each at most `limits[child]` times."""

    scalars: int
    children: frozenset[str]
    repeated: frozenset[str] = frozenset()


def node(scalars: int, *children: str, repeated: tuple[str, ...] = ()) -> Node:
    return Node(scalars, frozenset(children), frozenset(repeated))


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
# WKT 2 (GEOGCRS, PROJCRS and their parts); units are explicit, axes carry
# none (the unit of the coordinate system is a child of the CRS).
WKT2 = {
    "GEOGCRS": node(1, "DATUM", "PRIMEM", "CS", "AXIS", "ANGLEUNIT", "ID", repeated=("AXIS", "ID")),
    "PROJCRS": node(1, "BASEGEOGCRS", "CONVERSION", "CS", "AXIS", "LENGTHUNIT", "ID", repeated=("AXIS", "ID")),
    "BASEGEOGCRS": node(1, "DATUM", "PRIMEM", "ANGLEUNIT", "ID", repeated=("ID",)),
    "DATUM": node(1, "ELLIPSOID", "ID", repeated=("ID",)),
    "ELLIPSOID": node(3, "LENGTHUNIT", "ID", repeated=("ID",)),
    "PRIMEM": node(2, "ANGLEUNIT", "ID", repeated=("ID",)),
    "CS": node(2),
    "AXIS": node(2),
    "CONVERSION": node(1, "METHOD", "PARAMETER", "ID", repeated=("PARAMETER", "ID")),
    "METHOD": node(1, "ID", repeated=("ID",)),
    "PARAMETER": node(2, "ANGLEUNIT", "LENGTHUNIT", "SCALEUNIT", "ID", repeated=("ID",)),
    "ANGLEUNIT": node(2, "ID", repeated=("ID",)),
    "LENGTHUNIT": node(2, "ID", repeated=("ID",)),
    "SCALEUNIT": node(2, "ID", repeated=("ID",)),
    "ID": node(2),
}
WKT_ROOTS = {"wkt": {"GEOGCS", "PROJCS"}, "wkt2": {"GEOGCRS", "PROJCRS"}}

# PROJJSON: the members each object admits, and the objects its members hold.
ID_MEMBERS = {"authority", "code"}
UNIT_MEMBERS = {"type", "name", "conversion_factor"}
PROJJSON = {
    "GeographicCRS": {"$schema", "type", "name", "datum", "coordinate_system", "id", "ids"},
    "ProjectedCRS": {"$schema", "type", "name", "base_crs", "conversion", "coordinate_system", "id", "ids"},
    "base_crs": {"type", "name", "datum", "coordinate_system", "id", "ids"},
    "datum": {"type", "name", "ellipsoid", "prime_meridian", "id", "ids"},
    "ellipsoid": {"name", "semi_major_axis", "inverse_flattening", "id", "ids"},
    "prime_meridian": {"name", "longitude", "id", "ids"},
    "coordinate_system": {"subtype", "axis"},
    "axis": {"name", "abbreviation", "direction", "unit"},
    "conversion": {"name", "method", "parameters", "id", "ids"},
    "method": {"name", "id", "ids"},
    "parameter": {"name", "value", "unit", "id", "ids"},
    "value": {"value", "unit"},
}
PROJJSON_TYPES = {
    "base_crs": {"GeographicCRS"},
    "datum": {"GeodeticReferenceFrame"},
}


class Outside(Exception):
    """A node or member outside the closed grammar."""


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

    visit(root)


def check_projjson(root: Any) -> None:
    """Raise `Outside` unless every object and member is admitted."""

    def identifiers(holder: dict[str, Any]) -> None:
        found = [holder["id"]] if "id" in holder else holder.get("ids", [])
        if not isinstance(found, list):
            raise Outside("ids is not an array")
        for item in found:
            if not isinstance(item, dict) or set(item) - ID_MEMBERS:
                raise Outside("identifier member outside the grammar")

    def unit(value: Any) -> None:
        if isinstance(value, dict) and set(value) - UNIT_MEMBERS:
            raise Outside("unit member outside the grammar")

    def number(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) - PROJJSON["value"]:
                raise Outside("value member outside the grammar")
            unit(value.get("unit"))

    def visit(value: Any, kind: str) -> None:
        if not isinstance(value, dict):
            raise Outside("object expected")
        if set(value) - PROJJSON[kind]:
            raise Outside("member outside the grammar")
        if kind in PROJJSON_TYPES and "type" in value and value["type"] not in PROJJSON_TYPES[kind]:
            raise Outside("object type outside the grammar")
        identifiers(value)
        for member, child in (("datum", "datum"), ("ellipsoid", "ellipsoid"), ("prime_meridian", "prime_meridian"),
                              ("coordinate_system", "coordinate_system"), ("conversion", "conversion"),
                              ("method", "method"), ("base_crs", "base_crs")):
            if member in value:
                visit(value[member], child)
        for member in ("semi_major_axis", "inverse_flattening", "longitude", "value"):
            if member in value:
                number(value[member])
        if "unit" in value:
            unit(value["unit"])
        for member, child in (("axis", "axis"), ("parameters", "parameter")):
            if member in value:
                if not isinstance(value[member], list):
                    raise Outside("array expected")
                for item in value[member]:
                    visit(item, child)

    kind = root.get("type") if isinstance(root, dict) else None
    if kind not in ("GeographicCRS", "ProjectedCRS"):
        raise Outside("root type outside the grammar")
    visit(root, kind)
