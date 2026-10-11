"""The closed grammar of a verifiable CRS definition (Arrow Geometry Semantics
1.0, GEO-019).

A definition is verifiable only when it is made entirely of the nodes and
members listed here, each value of the exact kind listed (a text, a number,
a word from a closed set, an object of a given kind, an array of them);
anything else (a dynamic frame, a frame epoch, a datum ensemble other than a
reference one, a usage holding something else than its listed parts, a
member a future version of a format adds, a name given as an object) makes
it undecidable. The lists are the normative tables of GEO-019: the validator
and the specification state the same sets.

Usage metadata (`USAGE`, `SCOPE`, `AREA`, `BBOX`, `REMARK` and their
PROJJSON equivalents) is ignorable: it never enters the comparison, but its
content has a closed grammar of its own, so an unknown node inside it is
undecidable too.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, NamedTuple


class Outside(Exception):
    """A node, member or value outside the closed grammar."""


# --- WKT ---------------------------------------------------------------------

TEXT = frozenset({"string"})
NUMBER = frozenset({"number"})
CODE = frozenset({"string", "number"})
WORD = frozenset({"word"})
DIRECTIONS = frozenset({"north", "south", "east", "west", "up", "down"})
CS_TYPES = frozenset({"ellipsoidal", "cartesian"})


class Node(NamedTuple):
    """What a WKT node admits: exactly the scalar values in `values`, in
    order, each of one of the kinds listed (`words[i]` closes the words at
    position `i`, ASCII case-insensitively), and child nodes among
    `children`, each once unless it is in `repeated`."""

    values: tuple[frozenset[str], ...]
    children: frozenset[str]
    repeated: frozenset[str] = frozenset()
    words: tuple[tuple[int, frozenset[str]], ...] = ()


def node(values: tuple[frozenset[str], ...], *children: str, repeated: tuple[str, ...] = (),
         words: tuple[tuple[int, frozenset[str]], ...] = ()) -> Node:
    return Node(values, frozenset(children), frozenset(repeated), words)


NAMED = (TEXT,)
UNIT = (TEXT, NUMBER)
AXIS_VALUES = (TEXT, WORD)
AXIS_WORDS = ((1, DIRECTIONS),)

# WKT 1 (GEOGCS, PROJCS and their parts).
WKT1 = {
    "GEOGCS": node(NAMED, "DATUM", "PRIMEM", "UNIT", "AXIS", "AUTHORITY", repeated=("AXIS",)),
    "PROJCS": node(NAMED, "GEOGCS", "PROJECTION", "PARAMETER", "UNIT", "AXIS", "AUTHORITY",
                   repeated=("PARAMETER", "AXIS")),
    "DATUM": node(NAMED, "SPHEROID", "AUTHORITY"),
    "SPHEROID": node((TEXT, NUMBER, NUMBER), "AUTHORITY"),
    "PRIMEM": node(UNIT, "AUTHORITY"),
    "UNIT": node(UNIT, "AUTHORITY"),
    "AXIS": node(AXIS_VALUES, words=AXIS_WORDS),
    "PROJECTION": node(NAMED, "AUTHORITY"),
    "PARAMETER": node(UNIT),
    "AUTHORITY": node((TEXT, CODE)),
}
# The ignorable usage metadata a WKT 2 CRS may carry (GEO-019).
USAGE_CHILDREN = ("USAGE", "SCOPE", "AREA", "BBOX", "REMARK")
# WKT 2 (GEOGCRS, PROJCRS and their parts).
WKT2 = {
    "GEOGCRS": node(NAMED, "DATUM", "ENSEMBLE", "PRIMEM", "CS", "AXIS", "ANGLEUNIT", "ID", *USAGE_CHILDREN,
                    repeated=("AXIS", "ID", "USAGE")),
    "PROJCRS": node(NAMED, "BASEGEOGCRS", "CONVERSION", "CS", "AXIS", "LENGTHUNIT", "ID", *USAGE_CHILDREN,
                    repeated=("AXIS", "ID", "USAGE")),
    "BASEGEOGCRS": node(NAMED, "DATUM", "ENSEMBLE", "PRIMEM", "ANGLEUNIT", "ID", repeated=("ID",)),
    "DATUM": node(NAMED, "ELLIPSOID", "ID", repeated=("ID",)),
    "ENSEMBLE": node(NAMED, "MEMBER", "ELLIPSOID", "ENSEMBLEACCURACY", "ID", repeated=("MEMBER", "ID")),
    "MEMBER": node(NAMED, "ID", repeated=("ID",)),
    "ENSEMBLEACCURACY": node((NUMBER,)),
    "ELLIPSOID": node((TEXT, NUMBER, NUMBER), "LENGTHUNIT", "ID", repeated=("ID",)),
    "PRIMEM": node(UNIT, "ANGLEUNIT", "ID", repeated=("ID",)),
    "CS": node((WORD, NUMBER), words=((0, CS_TYPES),)),
    "AXIS": node(AXIS_VALUES, "ORDER", "ANGLEUNIT", "LENGTHUNIT", words=AXIS_WORDS),
    "ORDER": node((NUMBER,)),
    "CONVERSION": node(NAMED, "METHOD", "PARAMETER", "ID", repeated=("PARAMETER", "ID")),
    "METHOD": node(NAMED, "ID", repeated=("ID",)),
    "PARAMETER": node(UNIT, "ANGLEUNIT", "LENGTHUNIT", "SCALEUNIT", "ID", repeated=("ID",)),
    "ANGLEUNIT": node(UNIT, "ID", repeated=("ID",)),
    "LENGTHUNIT": node(UNIT, "ID", repeated=("ID",)),
    "SCALEUNIT": node(UNIT, "ID", repeated=("ID",)),
    "ID": node((TEXT, CODE)),
    "USAGE": node((), "SCOPE", "AREA", "BBOX", "ID", repeated=("ID",)),
    "SCOPE": node(NAMED),
    "AREA": node(NAMED),
    "BBOX": node((NUMBER, NUMBER, NUMBER, NUMBER)),
    "REMARK": node(NAMED),
}
WKT_ROOTS = {"wkt": {"GEOGCS", "PROJCS"}, "wkt2": {"GEOGCRS", "PROJCRS"}}


# --- PROJJSON -------------------------------------------------------------------

class Kind(NamedTuple):
    """The kind of a PROJJSON value: `json` is one of string, number, object,
    array; `values` closes a string; `object` names the members table of an
    object; `item` is the kind of an array's items; `alternatives` lists the
    other kinds a value may take."""

    json: str
    values: frozenset[str] | None = None
    object: str | None = None
    item: "Kind | None" = None
    alternatives: tuple["Kind", ...] = ()


STRING = Kind("string")
NUM = Kind("number")


def obj(name: str) -> Kind:
    return Kind("object", object=name)


def array(item: Kind) -> Kind:
    return Kind("array", item=item)


def one_of(*values: str) -> Kind:
    return Kind("string", values=frozenset(values))


ID_CODE = Kind("number", alternatives=(STRING,))
# A number is bare (in the default unit) or an object with its value and unit.
VALUE = Kind("number", alternatives=(obj("value"),))
# PROJJSON writes the three common units as a word, any other as an object.
UNIT_KIND = one_of("metre", "degree", "unity")._replace(alternatives=(obj("unit"),))
IDS = {"id": obj("id"), "ids": array(obj("id"))}
USAGE_MEMBERS = {
    "scope": STRING, "area": STRING, "bbox": obj("bbox"), "usages": array(obj("usage")), "remarks": STRING,
}
# Every member each object admits, and the exact kind of its value. A
# member absent from its table, or a value of another kind, is outside.
PROJJSON: dict[str, dict[str, Kind]] = {
    "GeographicCRS": {
        "$schema": STRING, "type": one_of("GeographicCRS"), "name": STRING, "datum": obj("datum"),
        "datum_ensemble": obj("datum_ensemble"), "coordinate_system": obj("coordinate_system"),
        **IDS, **USAGE_MEMBERS,
    },
    "ProjectedCRS": {
        "$schema": STRING, "type": one_of("ProjectedCRS"), "name": STRING, "base_crs": obj("base_crs"),
        "conversion": obj("conversion"), "coordinate_system": obj("coordinate_system"),
        **IDS, **USAGE_MEMBERS,
    },
    "base_crs": {
        "type": one_of("GeographicCRS"), "name": STRING, "datum": obj("datum"),
        "datum_ensemble": obj("datum_ensemble"), "coordinate_system": obj("coordinate_system"), **IDS,
    },
    "datum": {
        "type": one_of("GeodeticReferenceFrame"), "name": STRING, "ellipsoid": obj("ellipsoid"),
        "prime_meridian": obj("prime_meridian"), **IDS,
    },
    "datum_ensemble": {
        "type": one_of("DatumEnsemble"), "name": STRING, "members": array(obj("member")),
        "ellipsoid": obj("ellipsoid"), "accuracy": STRING, **IDS,
    },
    "member": {"name": STRING, **IDS},
    "ellipsoid": {"name": STRING, "semi_major_axis": VALUE, "inverse_flattening": VALUE, **IDS},
    "prime_meridian": {"name": STRING, "longitude": VALUE, **IDS},
    "coordinate_system": {"subtype": one_of("ellipsoidal", "Cartesian"), "axis": array(obj("axis"))},
    "axis": {"name": STRING, "abbreviation": STRING, "direction": one_of(*sorted(DIRECTIONS)), "unit": UNIT_KIND},
    "conversion": {"name": STRING, "method": obj("method"), "parameters": array(obj("parameter")), **IDS},
    "method": {"name": STRING, **IDS},
    "parameter": {"name": STRING, "value": VALUE, "unit": UNIT_KIND, **IDS},
    "value": {"value": NUM, "unit": UNIT_KIND},
    "unit": {
        "type": one_of("LinearUnit", "AngularUnit", "ScaleUnit", "Unit"), "name": STRING,
        "conversion_factor": NUM, **IDS,
    },
    "id": {"authority": STRING, "code": ID_CODE},
    "usage": {"scope": STRING, "area": STRING, "bbox": obj("bbox"), **IDS},
    "bbox": {"south_latitude": NUM, "west_longitude": NUM, "north_latitude": NUM, "east_longitude": NUM},
}
# The members an object must hold for its form to be readable.
REQUIRED = {
    "value": {"value"},
    "id": {"authority", "code"},
    "bbox": {"south_latitude", "west_longitude", "north_latitude", "east_longitude"},
    "unit": {"name", "conversion_factor"},
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


def _is_node(item: Any) -> bool:
    return hasattr(item, "keyword")


def _wkt_children(current: Any, keyword: str) -> list[Any]:
    return [item for item in current.items if _is_node(item) and item.keyword.upper() == keyword]


def _wkt_ids(current: Any) -> list[tuple[str, str]]:
    return [(item.items[0][1], _code_text(*item.items[1])) for item in _wkt_children(current, "ID")]


def wkt_ensemble(current: Any) -> Ensemble:
    """The reference ensemble a WKT 2 `ENSEMBLE` node is identical to."""
    try:
        members = [(member.items[0][1], _wkt_ids(member)) for member in _wkt_children(current, "MEMBER")]
        accuracies = _wkt_children(current, "ENSEMBLEACCURACY")
        accuracy = accuracies[0].items[0][1] if len(accuracies) == 1 else None
        name = current.items[0][1]
    except (IndexError, TypeError) as error:
        raise Outside("ensemble outside the grammar") from error
    return _match_ensemble(name, members, accuracy, _wkt_ids(current))


def _projjson_ids(holder: Any) -> list[tuple[str, str]]:
    if not isinstance(holder, dict) or ("id" in holder and "ids" in holder):
        raise Outside("identifiers outside the grammar")
    found = [holder["id"]] if "id" in holder else holder.get("ids", [])
    if not isinstance(found, list) or not all(
        isinstance(item, dict) and isinstance(item.get("authority"), str)
        and _json_kind(item.get("code")) in ("number", "string")
        for item in found
    ):
        raise Outside("identifiers outside the grammar")
    return [(item["authority"], str(item["code"])) for item in found]


def projjson_ensemble(value: dict[str, Any]) -> Ensemble:
    """The reference ensemble a PROJJSON `datum_ensemble`, already admitted
    by the grammar, is identical to."""
    members = value.get("members")
    if not isinstance(members, list) or not all(isinstance(member, dict) for member in members):
        raise Outside("ensemble members outside the grammar")
    return _match_ensemble(
        value.get("name"),
        [(member.get("name"), _projjson_ids(member)) for member in members],
        value.get("accuracy"),
        _projjson_ids(value),
    )


def check_wkt(root: Any, definition_format: str) -> None:
    """Raise `Outside` unless every node and value of the parsed WKT is
    admitted."""
    grammar = WKT2 if definition_format == "wkt2" else WKT1
    if root.keyword.upper() not in WKT_ROOTS[definition_format]:
        raise Outside("root keyword outside the grammar")

    def visit(current: Any) -> None:
        rule = grammar.get(current.keyword.upper())
        if rule is None:
            raise Outside("keyword outside the grammar")
        # The values come first, then the children.
        values = [item for item in current.items if not _is_node(item)]
        if current.items[: len(values)] != values or len(values) != len(rule.values):
            raise Outside("values missing, in excess or after a child")
        for position, (item, kinds) in enumerate(zip(values, rule.values)):
            if item[0] not in kinds:
                raise Outside("value of another kind")
        for position, allowed in rule.words:
            if values[position][1].lower() not in allowed:
                raise Outside("word outside its closed set")
        seen: dict[str, int] = {}
        for item in current.items[len(values):]:
            keyword = item.keyword.upper()
            if keyword not in rule.children:
                raise Outside("child outside the grammar")
            seen[keyword] = seen.get(keyword, 0) + 1
            if seen[keyword] > 1 and keyword not in rule.repeated:
                raise Outside("child repeated")
            visit(item)
        for item in _wkt_children(current, "ID") + _wkt_children(current, "AUTHORITY"):
            _code_text(*item.items[1])
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


def _json_kind(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return "other"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, Decimal)):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "other"


def check_projjson(root: Any) -> None:
    """Raise `Outside` unless every member is admitted, with a value of
    exactly the kind its table states."""

    def value_of(value: Any, kind: Kind) -> None:
        for candidate in (kind, *kind.alternatives):
            if _json_kind(value) != candidate.json:
                continue
            if candidate.values is not None and value not in candidate.values:
                continue
            if candidate.object is not None:
                visit(value, candidate.object)
            if candidate.item is not None:
                for item in value:
                    value_of(item, candidate.item)
            return
        raise Outside("value of another kind")

    def visit(value: dict[str, Any], name: str) -> None:
        table = PROJJSON[name]
        if set(value) - set(table) or REQUIRED.get(name, set()) - set(value):
            raise Outside("member outside the grammar or missing")
        if "id" in value and "ids" in value:
            raise Outside("both id and ids")
        if "datum" in value and "datum_ensemble" in value:
            raise Outside("both a datum and a datum ensemble")
        for member, child in value.items():
            value_of(child, table[member])
        if name == "datum_ensemble":
            projjson_ensemble(value)

    if not isinstance(root, dict) or root.get("type") not in ("GeographicCRS", "ProjectedCRS"):
        raise Outside("root type outside the grammar")
    visit(root, root["type"])
