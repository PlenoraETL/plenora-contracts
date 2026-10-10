"""Interoperability vectors (Composition 1.0, section 6, COMP-001 to COMP-005).

Each vector is checked against the rules, never trusted: the expected table
of a handoff is recomputed from its input and the declared transformations,
every chain is checked against the composition matrix, every rejection
against its input vector and Arrow Interchange 1.0 ARROW-013, and every
source document is read here.
"""

from __future__ import annotations

import copy
import json
import re
import struct
from pathlib import Path
from typing import Any, Callable

import arrow_data

GEOMETRY = "plenora.geometry."
CLASS_CATEGORY = {"support": "unsupported", "crs": "crs"}
# ARROW-014: the value classes; everything else is decided from the schema.
VALUE_RULES = {"VOC-008", "VOC-009", "VOC-011"}
# COMP-003: who may declare each transformation; `None` is any step.
TRANSFORMATION_OWNERS: dict[str, set[tuple[str, str]] | None] = {
    "assign_field_ids": None,
    "large_to_standard": {("plenora-data-tools", "data.run")},
    "srid_from_epsg_identifier": {("plenora-data-tools", "data.run")},
    "ewkb_with_field_srid": {("plenora-database-tools", "database.read")},
    "axis_order_unknown": {("plenora-database-tools", "database.read")},
    "several_types_to_mixed": {("plenora-database-tools", "database.read")},
    "provider_metadata": {("plenora-database-tools", "database.read")},
}
IPC_FORMATS = {"arrow_ipc_file", "arrow_ipc_stream"}
NORTH_FIRST = {"lat_lon", "northing_easting"}
RESERVED_PREFIXES = ("plenora.geometry.", "plenora.contract.", "plenora.field_id")
EPSG = re.compile(r"^EPSG:([1-9][0-9]*)$")


# --- transformations (COMP-003) -------------------------------------------------

def _metadata(field: dict[str, Any]) -> dict[str, str]:
    return field["metadata"]


def assign_field_ids(table: dict[str, Any]) -> None:
    """VOC-013: the smallest free identifier, in field order."""
    used = {
        int(_metadata(field)["plenora.field_id"])
        for field in table["fields"]
        if "plenora.field_id" in _metadata(field)
    }
    candidate = 0
    for field in table["fields"]:
        if "plenora.field_id" in _metadata(field):
            continue
        while candidate in used:
            candidate += 1
        _metadata(field)["plenora.field_id"] = str(candidate)
        used.add(candidate)


def large_to_standard(table: dict[str, Any]) -> None:
    for field in table["fields"]:
        field["type"] = {"large_utf8": "utf8", "large_binary": "binary"}.get(field["type"], field["type"])


def srid_from_epsg_identifier(table: dict[str, Any]) -> None:
    for field in filter(arrow_data.is_geometry, table["fields"]):
        metadata = _metadata(field)
        match = EPSG.match(metadata.get(GEOMETRY + "crs_id", ""))
        if (
            match
            and metadata[GEOMETRY + "crs_resolution"] == "resolved"
            and GEOMETRY + "srid" not in metadata
            and int(match.group(1)) < 2**31
        ):
            metadata[GEOMETRY + "srid"] = match.group(1)


def _with_srid(value: bytes, srid: int) -> bytes:
    order = value[0]
    prefix = "<" if order == 1 else ">"
    (code,) = struct.unpack(prefix + "I", value[1:5])
    if code & arrow_data.FLAG_SRID:
        (present,) = struct.unpack(prefix + "i", value[5:9])
        if present != srid:
            raise ValueError("EWKB SRID differs from the field")
        return value
    return value[:1] + struct.pack(prefix + "I", code | arrow_data.FLAG_SRID) + struct.pack(prefix + "i", srid) + value[5:]


def ewkb_with_field_srid(table: dict[str, Any]) -> None:
    """VOC-009: EWKB carrying the field's SRID on the outermost geometry."""
    for field in filter(arrow_data.is_geometry, table["fields"]):
        metadata = _metadata(field)
        metadata[GEOMETRY + "encoding"] = "ewkb"
        srid = metadata.get(GEOMETRY + "srid")
        if srid is None:
            continue
        for row in table["rows"]:
            if row[field["name"]] is not None:
                row[field["name"]] = _with_srid(bytes.fromhex(row[field["name"]]), int(srid)).hex()


def axis_order_unknown(table: dict[str, Any]) -> None:
    for field in filter(arrow_data.is_geometry, table["fields"]):
        metadata = _metadata(field)
        if metadata[GEOMETRY + "crs_resolution"] != "missing":
            metadata[GEOMETRY + "axis_order"] = "unknown"


def several_types_to_mixed(table: dict[str, Any]) -> None:
    """VOC-010: a target that keeps several types in an unconstrained column
    reads them back as `mixed`, without the list."""
    for field in filter(arrow_data.is_geometry, table["fields"]):
        metadata = _metadata(field)
        types = arrow_data._type_list(metadata.get(GEOMETRY + "types"))
        if metadata[GEOMETRY + "types_declaration"] == "exact" and types and len(types) > 1:
            metadata[GEOMETRY + "types_declaration"] = "mixed"
            del metadata[GEOMETRY + "types"]


def provider_metadata(table: dict[str, Any]) -> None:
    """ARROW-009: provider keys are verified by the provider's own vectors."""


TRANSFORMATIONS: dict[str, Callable[[dict[str, Any]], None]] = {
    "assign_field_ids": assign_field_ids,
    "large_to_standard": large_to_standard,
    "srid_from_epsg_identifier": srid_from_epsg_identifier,
    "ewkb_with_field_srid": ewkb_with_field_srid,
    "axis_order_unknown": axis_order_unknown,
    "several_types_to_mixed": several_types_to_mixed,
    "provider_metadata": provider_metadata,
}


def expected_output(table: dict[str, Any], chain: list[dict[str, Any]]) -> dict[str, Any]:
    """COMP-003: a step applies its transformations in the order of the table."""
    result = {
        "schema_metadata": dict(table["schema_metadata"]),
        "fields": copy.deepcopy(table["fields"]),
        "rows": copy.deepcopy(table["rows"]),
    }
    for step in chain:
        for name in TRANSFORMATIONS:
            if name in step["transformations"]:
                TRANSFORMATIONS[name](result)
    return result


def same(left: Any, right: Any) -> bool:
    """Equality that tells 1 from 1.0 and from true."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(map(same, left, right))
    return left == right


def computes(step: dict[str, Any], kernels: set[str]) -> bool:
    """A step that computes with coordinates: `data.run` whose plan is a
    registered `geo.` kernel."""
    plan = (step.get("params") or {}).get("plan")
    return (
        step["operation"] == "data.run"
        and isinstance(plan, str)
        and plan.startswith("geo.")
        and plan in kernels
    )


def decodes(step: dict[str, Any], kernels: set[str]) -> bool:
    """A step that decodes geometry values (VOC-009, VOC-011): one that
    computes, or one that writes them to a target that interprets them."""
    if computes(step, kernels):
        return True
    if step["operation"] == "database.write":
        return True
    return step["operation"] == "io.write" and (step.get("params") or {}).get("format") not in IPC_FORMATS


# --- chains (COMP-002) ---------------------------------------------------------

Key = tuple[str, str, int]


def step_key(step: dict[str, Any]) -> Key:
    return (step["component"], step["operation"], step["version"])


def chain_errors(
    chain: list[dict[str, Any]],
    operations: dict[Key, dict[str, Any]],
    direct_edges: set[tuple[Key, Key]],
) -> list[str]:
    errors = []
    for step in chain:
        if step_key(step) not in operations:
            errors.append(f"names unknown operation {step_key(step)}")
        for name in step["transformations"]:
            owners = TRANSFORMATION_OWNERS[name]
            if owners is not None and (step["component"], step["operation"]) not in owners:
                errors.append(f"{step['operation']} cannot declare {name} (COMP-003)")
        prefix = step.get("provider_prefix")
        if prefix is not None and prefix.startswith(RESERVED_PREFIXES):
            errors.append(f"provider prefix {prefix} is reserved for the shared vocabulary")
    if chain and chain[0].get("via") == "target":
        errors.append("the first step cannot read a target no step wrote")
    for before, after in zip(chain, chain[1:]):
        if after.get("via") == "target":
            if (
                before["component"] != after["component"]
                or not before["operation"].endswith(".write")
                or not after["operation"].endswith(".read")
            ):
                errors.append(
                    f"{before['operation']} -> {after['operation']} is not a write then a read of one component"
                )
        elif (step_key(before), step_key(after)) not in direct_edges:
            errors.append(f"{before['operation']} -> {after['operation']} is not a direct edge of the matrix")
    return errors


# --- rejections (COMP-004) -------------------------------------------------------

def rejection_errors(vector: dict[str, Any], table: dict[str, Any], kernels: set[str]) -> list[str]:
    expected = vector["expected_error"]
    step = vector["chain"][0]
    found = arrow_data.verdict(table)
    errors = []
    value_class = False
    if found is not None:
        value_class = found.rule in VALUE_RULES
        if expected["class"] != "input":
            errors.append(f"an invalid input is class input, not {expected['class']}")
        if expected["category"] != found.category:
            errors.append(f"expects {expected['category']}, the input vector gives {found.category}")
        if found.rule not in expected["rules"]:
            errors.append(f"does not cite {found.rule}, the rule that rejects the input")
        if value_class and not decodes(step, kernels):
            errors.append(f"{step['operation']} carries values without decoding them (VOC-009, VOC-011)")
    else:
        if expected["class"] == "input":
            errors.append("a valid input cannot be rejected as class input")
            return errors
        if expected["category"] != CLASS_CATEGORY[expected["class"]]:
            errors.append(f"class {expected['class']} is {CLASS_CATEGORY[expected['class']]} (ARROW-013)")
        geometry = list(filter(arrow_data.is_geometry, table["fields"]))
        rules = set(expected["rules"])
        if expected["class"] == "support":
            several_fields = len(geometry) > 1
            several_types = any(
                len((arrow_data._type_list(arrow_data_metadata(field).get(GEOMETRY + "types")) or [])) > 1
                for field in geometry
            )
            if not ("VOC-012" in rules and several_fields) and not ("VOC-010" in rules and several_types):
                errors.append("a support rejection cites VOC-012 or VOC-010 for an input that shows it")
        if expected["class"] == "crs":
            if not computes(step, kernels):
                errors.append("a crs rejection of a valid input needs a step that computes (VOC-004)")
            declared = [
                field for field in geometry
                if arrow_data_metadata(field)[GEOMETRY + "crs_resolution"] != "missing"
            ]
            try:
                computed = next(filter(None, map(arrow_data.computation_verdict, declared)), None)
            except arrow_data.Undecidable:
                computed = None
            north_first = any(arrow_data_metadata(field).get(GEOMETRY + "axis_order") in NORTH_FIRST for field in geometry)
            by_vocabulary = computed is not None and computed.rule in rules
            by_profile = "DT-ARROW-004" in rules and north_first
            if not (by_vocabulary or by_profile):
                errors.append("a crs rejection of a valid input cites the rule that refuses the computation")
    if value_class:
        writes = step["operation"].endswith(".write")
        phases = {"write"} if writes else {"read"}
        effects = {"none", "rolled_back"} if writes else {"none"}
    else:
        phases, effects = {"validate"}, {"none"}
    if set(expected["phases"]) != phases:
        errors.append(f"expects phases {sorted(expected['phases'])}, the class gives {sorted(phases)}")
    if set(expected["remote_effects"]) != effects:
        errors.append(f"expects remote effects {sorted(expected['remote_effects'])}, the class gives {sorted(effects)}")
    return errors


def arrow_data_metadata(field: dict[str, Any]) -> dict[str, str]:
    return field["metadata"]


# --- sources (VOC-002, VOC-003) ----------------------------------------------------

def geojson_coordinates(text: str) -> list[list[float]]:
    """The point coordinates of a GeoJSON FeatureCollection, as stored."""
    document = json.loads(text)
    if document.get("type") != "FeatureCollection":
        raise ValueError("not a FeatureCollection")
    coordinates = []
    for feature in document["features"]:
        geometry = feature["geometry"]
        if geometry["type"] != "Point" or len(geometry["coordinates"]) != 2:
            raise ValueError("only two-dimensional points are read here")
        coordinates.append([float(value) for value in geometry["coordinates"]])
    return coordinates


def source_errors(vector: dict[str, Any]) -> list[str]:
    expected = vector["expected_geometry"]
    errors = []
    # RFC 7946: WGS 84, longitude then latitude, whatever any crs member says.
    if expected["crs_id"] != "OGC:CRS84":
        errors.append("a GeoJSON source declares OGC:CRS84 (RFC 7946)")
    if expected["axis_order"] != "lon_lat":
        errors.append("a GeoJSON source stores longitude first (VOC-002)")
    try:
        found = geojson_coordinates(vector["source"]["text"])
    except (ValueError, KeyError, TypeError) as problem:
        return errors + [f"source is not readable: {problem}"]
    if found != [[float(x), float(y)] for x, y in expected["coordinates"]]:
        errors.append("expected coordinates differ from the stored ones")
    if not any(abs(x) > 90 for x, _ in found):
        errors.append("no longitude beyond 90 degrees: an exchanged order would pass unnoticed (VOC-003)")
    step = vector["chain"][0]
    if (step["component"], step["operation"]) != ("plenora-io-tools", "io.read") or step["transformations"]:
        errors.append("a source is read by io.read, without transformations")
    return errors


# --- the gate ----------------------------------------------------------------------

def vector_errors(
    path: Path,
    vector: dict[str, Any],
    operations: dict[Key, dict[str, Any]],
    direct_edges: set[tuple[Key, Key]],
    load: Callable[[Path], Any],
    kernels: set[str] = frozenset(),
) -> list[str]:
    errors = chain_errors(vector["chain"], operations, direct_edges)
    if vector["kind"] == "source":
        return errors + source_errors(vector)
    input_path = (path.parent / vector["input"]).resolve()
    if not input_path.exists():
        return errors + [f"input {vector['input']} does not exist"]
    table = load(input_path)
    try:
        if vector["kind"] == "rejection":
            return errors + rejection_errors(vector, table, kernels)
        if table["expect"] != "valid" or arrow_data.verdict(table) is not None:
            return errors + ["a handoff starts from a valid input"]
    except arrow_data.FixtureError as problem:
        # Its own gate reports the input; here it cannot be an input.
        return errors + [f"input {vector['input']} is not a buildable table: {problem}"]
    try:
        expected = expected_output(table, vector["chain"])
    except ValueError as problem:
        return errors + [f"transformations cannot apply: {problem}"]
    if not same(vector["expected_output"], expected):
        errors.append("expected_output differs from the input with the declared transformations")
    produced = dict(expected, expect="valid")
    if arrow_data.verdict(produced) is not None:
        errors.append("the expected output is not a valid table of the vocabulary")
    return errors
