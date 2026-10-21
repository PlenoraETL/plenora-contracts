"""Interoperability vectors (Interoperability Vectors 1.0, INTEROP-001 to INTEROP-005).

Each vector is checked against the rules, never trusted: every step of a
chain is evaluated in the single order of Arrow Geometry Semantics 1.0
(REJ-002), the operation included; the expected table of a handoff is
recomputed from its input and the declared transformations; every chain is
checked against the composition matrix; every source document is read here.
Error messages name rules and paths, never a value of a vector.
"""

from __future__ import annotations

import copy
import csv
import io
import json
import re
import struct
from pathlib import Path
from typing import Any, Callable, NamedTuple

import arrow_data

GEOMETRY = "plenora.geometry."
# REJ-002: the value classes; everything else is decided from the schema.
VALUE_RULES = {"GEO-008", "GEO-009", "GEO-011"}
CLASS_CATEGORY = {"support": "unsupported", "crs": "crs"}
DATA_RUN = ("plenora-data-tools", "data.run")
DATABASE_READ = ("plenora-database-tools", "database.read")
# INTEROP-003: who may declare each transformation; `None` is any step.
TRANSFORMATION_OWNERS: dict[str, set[tuple[str, str]] | None] = {
    "complete_missing_geometry_keys": {DATA_RUN},
    "assign_field_ids": None,
    "large_to_standard": {DATA_RUN},
    "srid_from_epsg_identifier": {DATA_RUN},
    "ewkb_with_field_srid": {DATABASE_READ},
    "axis_order_unknown": {DATABASE_READ},
    "several_types_to_mixed": {DATABASE_READ},
    "provider_metadata": {DATABASE_READ},
}
# Declared component limits a step may name (GEO-010, GEO-012).
LIMITS = {"one_geometry_field": "GEO-012", "one_geometry_type": "GEO-010"}
IPC_FORMATS = {"arrow_ipc_file", "arrow_ipc_stream"}
# INTEROP-002: the catalog input contracts whose request selects the format of
# the document a step reads (source) or writes (sink). Only for these is the
# `format` of a step a format: the catalog sides of `database.read` and
# `database.write` equal those of `io.read` and `io.write`, but their input
# contracts select no format.
SOURCE_FORMAT_INPUTS = {"plenora-io-read-input-v1"}
SINK_FORMAT_INPUTS = {"plenora-io-write-input-v1"}
# INTEROP-002: the closed list of the abstract formats a step may name; a
# new format, like a new input contract that selects one, is added here and
# in the specification explicitly.
FORMATS = IPC_FORMATS | {"gpkg", "geojson", "wkt_csv"}


def _params(step: dict[str, Any]) -> dict[str, Any]:
    """The step's parameters, an open object in the schema; anything else
    reads as none (`step_errors` reports it and stops the evaluation)."""
    params = step.get("params", {})
    return params if isinstance(params, dict) else {}


def _format(step: dict[str, Any]) -> Any:
    return _params(step).get("format")


def _known_format(value: Any) -> bool:
    return isinstance(value, str) and value in FORMATS
ARROW_INTERCHANGE = "plenora-arrow-interchange-v1"
ARROW_MEDIA_TYPES = {"application/vnd.apache.arrow.stream", "application/vnd.apache.arrow.file"}
NORTH_FIRST = {"lat_lon", "northing_easting"}
RESERVED_PREFIXES = ("plenora.geometry.", "plenora.contract.", "plenora.field_id")
EPSG = re.compile(r"EPSG:([1-9][0-9]*)")
UTM = re.compile(r"EPSG:32[67][0-9]{2}")


def _metadata(field: dict[str, Any]) -> dict[str, str]:
    return field["metadata"]


def _geometry(table: dict[str, Any]) -> list[dict[str, Any]]:
    return list(filter(arrow_data.is_geometry, table["fields"]))


# --- transformations (INTEROP-003) ------------------------------------------------

# DT-ARROW-003: what data-tools reads for a key the field omits.
PROFILE_DEFAULTS = {
    GEOMETRY + "encoding": "wkb",
    GEOMETRY + "dimensions": "unknown",
    GEOMETRY + "types_declaration": "unresolved",
    GEOMETRY + "spatial_semantics": "geometry",
    GEOMETRY + "precision": "float64",
}


def complete_missing_geometry_keys(table: dict[str, Any]) -> None:
    """DT-ARROW-003: the keys a geometry field omits, read without asserting
    more than the field carries."""
    for field in _geometry(table):
        metadata = _metadata(field)
        for key, value in PROFILE_DEFAULTS.items():
            metadata.setdefault(key, value)
        declared = GEOMETRY + "crs_id" in metadata or GEOMETRY + "crs_definition" in metadata
        if GEOMETRY + "crs_resolution" not in metadata:
            metadata[GEOMETRY + "crs_resolution"] = "declared_unresolved" if declared else "missing"
        if declared and GEOMETRY + "axis_order" not in metadata:
            # An order the field does not state is not asserted (GEO-002).
            metadata[GEOMETRY + "axis_order"] = "unknown"


def assign_field_ids(table: dict[str, Any]) -> None:
    """GEO-013: the smallest free identifier, in field order."""
    used = {
        int(_metadata(field)["plenora.field_id"])
        for field in table["fields"]
        if arrow_data.DECIMAL.fullmatch(_metadata(field).get("plenora.field_id", ""))
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
    for field in _geometry(table):
        metadata = _metadata(field)
        match = EPSG.fullmatch(metadata.get(GEOMETRY + "crs_id", ""))
        if (
            match
            and metadata[GEOMETRY + "crs_resolution"] == "resolved"
            and GEOMETRY + "srid" not in metadata
            and int(match.group(1)) < 2**31
        ):
            metadata[GEOMETRY + "srid"] = match.group(1)


def with_srid(value: bytes, srid: int) -> bytes:
    """GEO-009: the extended type code, SRID flag and SRID on the outermost
    geometry; an ISO dimension code becomes the extended flags first."""
    prefix = "<" if value[0] == 1 else ">"
    (code,) = struct.unpack(prefix + "I", value[1:5])
    if code & arrow_data.FLAG_SRID:
        (present,) = struct.unpack(prefix + "i", value[5:9])
        if present != srid:
            raise ValueError("EWKB SRID differs from the field")
        return value
    thousands, kind = divmod(code & 0x1FFFFFFF, 1000)
    flags = code & (arrow_data.FLAG_Z | arrow_data.FLAG_M)
    if thousands:
        has_z, has_m = arrow_data.ISO_DIMENSIONS[thousands]
        flags = (arrow_data.FLAG_Z if has_z else 0) | (arrow_data.FLAG_M if has_m else 0)
    extended = kind | flags | arrow_data.FLAG_SRID
    return value[:1] + struct.pack(prefix + "I", extended) + struct.pack(prefix + "i", srid) + value[5:]


def ewkb_with_field_srid(table: dict[str, Any]) -> None:
    """GEO-009: EWKB carrying the field's SRID on the outermost geometry."""
    for field in _geometry(table):
        metadata = _metadata(field)
        metadata[GEOMETRY + "encoding"] = "ewkb"
        srid = metadata.get(GEOMETRY + "srid")
        if srid is None:
            continue
        for row in table["rows"]:
            if row[field["name"]] is not None:
                row[field["name"]] = with_srid(bytes.fromhex(row[field["name"]]), int(srid)).hex()


def axis_order_unknown(table: dict[str, Any]) -> None:
    for field in _geometry(table):
        metadata = _metadata(field)
        if metadata[GEOMETRY + "crs_resolution"] != "missing":
            metadata[GEOMETRY + "axis_order"] = "unknown"


def several_types_to_mixed(table: dict[str, Any]) -> None:
    """GEO-010: a target that keeps several types in an unconstrained column
    reads them back as `mixed`, without the list."""
    for field in _geometry(table):
        metadata = _metadata(field)
        types = arrow_data._type_list(metadata.get(GEOMETRY + "types"))
        if metadata[GEOMETRY + "types_declaration"] == "exact" and types and len(types) > 1:
            metadata[GEOMETRY + "types_declaration"] = "mixed"
            del metadata[GEOMETRY + "types"]


def provider_metadata(table: dict[str, Any]) -> None:
    """ARROW-009: provider keys are delegated (`delegated_metadata`). Their
    values and their survival along the chain are observed by the harness
    that runs the chain and by the provider's own vectors (INTEROP-003); this
    validator, which runs no component, only checks that the prefixes are
    declared."""


TRANSFORMATIONS: dict[str, Callable[[dict[str, Any]], None]] = {
    "complete_missing_geometry_keys": complete_missing_geometry_keys,
    "assign_field_ids": assign_field_ids,
    "large_to_standard": large_to_standard,
    "srid_from_epsg_identifier": srid_from_epsg_identifier,
    "ewkb_with_field_srid": ewkb_with_field_srid,
    "axis_order_unknown": axis_order_unknown,
    "several_types_to_mixed": several_types_to_mixed,
    "provider_metadata": provider_metadata,
}


def apply(table: dict[str, Any], step: dict[str, Any]) -> None:
    """INTEROP-003: a step applies its transformations in the order of the table."""
    for name in TRANSFORMATIONS:
        if name in step["transformations"]:
            TRANSFORMATIONS[name](table)


def _copy(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_metadata": dict(table["schema_metadata"]),
        "fields": copy.deepcopy(table["fields"]),
        "rows": copy.deepcopy(table["rows"]),
    }


def expected_output(table: dict[str, Any], chain: list[dict[str, Any]]) -> dict[str, Any]:
    result = _copy(table)
    for step in chain:
        apply(result, step)
    prefixes = sorted({step["provider_prefix"] for step in chain if "provider_prefix" in step})
    if prefixes:
        result["delegated_metadata"] = prefixes
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


# Keys of the vector's own structure; a field name, a row key or a metadata
# key may be data and is named by its position among the sorted keys.
STRUCTURAL_KEYS = {"schema_metadata", "fields", "rows", "delegated_metadata", "name", "type", "nullable", "metadata"}


def difference(left: Any, right: Any, path: str = "") -> str | None:
    """The path of the first difference, never a value or a data key."""
    if type(left) is not type(right):
        return path or "/"
    if isinstance(left, dict):
        data_map = path.endswith(("/metadata", "/schema_metadata")) or "/rows/" in path + "/"
        for position, key in enumerate(sorted(set(left) | set(right))):
            segment = key if key in STRUCTURAL_KEYS and not data_map else f"#{position}"
            if key not in left or key not in right:
                return f"{path}/{segment}"
            found = difference(left[key], right[key], f"{path}/{segment}")
            if found:
                return found
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path} (length)"
        for index, (one, other) in enumerate(zip(left, right)):
            found = difference(one, other, f"{path}/{index}")
            if found:
                return found
        return None
    return None if left == right else (path or "/")


def _table_shape(table: Any) -> bool:
    """The open output fixtures must be checked before Arrow rules read them."""
    def metadata(value: Any) -> bool:
        return isinstance(value, dict) and all(isinstance(item, str) for item in value.values())

    if not isinstance(table, dict) or not metadata(table.get("schema_metadata")):
        return False
    fields, rows = table.get("fields"), table.get("rows")
    return (
        isinstance(fields, list) and bool(fields)
        and all(
            isinstance(field, dict)
            and isinstance(field.get("name"), str) and bool(field["name"])
            and isinstance(field.get("type"), str)
            and field["type"] in {"bool", "int32", "int64", "float64", "utf8", "large_utf8", "binary", "large_binary"}
            and isinstance(field.get("nullable"), bool)
            and metadata(field.get("metadata"))
            for field in fields
        )
        and isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
    )


def output_errors(vector: dict[str, Any], table: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Decision 0022: compare a result, allowing only declared fresh IDs to vary."""
    if not all(_table_shape(value) for value in (table, vector.get("expected_output"), actual)):
        return ["output comparison requires well-formed table fixtures"]
    positions = vector.get("assigned_field_ids", [])
    if not isinstance(positions, list) or any(
        not isinstance(position, int) or isinstance(position, bool) or position < 0
        for position in positions
    ):
        return ["assigned field positions must be nonnegative integers"]
    compared = copy.deepcopy(actual)
    errors = []
    for position in positions:
        if position >= min(len(table["fields"]), len(compared["fields"]),
                           len(vector["expected_output"]["fields"])):
            errors.append("assigned field position is outside the table")
            continue
        incoming = table["fields"][position]["metadata"]
        expected = vector["expected_output"]["fields"][position].get("metadata")
        metadata = compared["fields"][position]["metadata"]
        if (not isinstance(expected, dict) or "plenora.field_id" in incoming
                or "plenora.field_id" in expected):
            errors.append("assigned field must omit its incoming and expected field id")
        value = metadata.pop("plenora.field_id", None)
        if not isinstance(value, str) or not arrow_data.DECIMAL.fullmatch(value):
            errors.append("assigned field id must be a canonical decimal")
    where = difference(vector["expected_output"], compared)
    if where is not None:
        errors.append(f"expected_output differs from the recomputed table at {where}")
    try:
        rejected = arrow_data.verdict(dict(actual, expect="valid")) is not None
    except arrow_data.FixtureError:
        # A malformed fixture is a document rejection, not a validator defect.
        return errors + ["the output is not a buildable table"]
    if rejected:
        errors.append("the expected output is not a valid table of the vocabulary")
    return errors


def surface_output_errors(
    vector: dict[str, Any], table: dict[str, Any], outputs: dict[str, dict[str, Any]]
) -> list[str]:
    """Decision 0022 rule 3: readings of one operation on the same store.

    Each output may choose fresh IDs, but every surface must observe the
    same assignment. Surface labels and table data never enter diagnostics.
    """
    if not isinstance(outputs, dict) or len(outputs) < 2:
        return ["at least two surface outputs are required (decision 0022 rule 3)"]
    errors = []
    reference = next(iter(outputs.values()))
    for position, actual in enumerate(outputs.values()):
        errors.extend(f"surface {position}: {error}" for error in output_errors(vector, table, actual))
        where = difference(reference, actual)
        if where is not None:
            errors.append(
                f"surface {position} differs from the first surface at {where} (decision 0022 rule 3)"
            )
    return errors


# --- the operation in the order (REJ-002) ----------------------------------------

def computes(step: dict[str, Any], kernels: set[str]) -> bool:
    """A step that computes with coordinates: `data.run` whose plan is a
    registered `geo.` kernel."""
    plan = _params(step).get("plan")
    return (
        step["operation"] == "data.run"
        and isinstance(plan, str)
        and plan.startswith("geo.")
        and plan in kernels
    )


def decodes(step: dict[str, Any], kernels: set[str]) -> bool:
    """A step that decodes geometry values (GEO-009, GEO-011): one that
    computes, or one that writes them to a target that interprets them."""
    if computes(step, kernels):
        return True
    if step["operation"] == "database.write":
        return True
    return step["operation"] == "io.write" and not _names_ipc_format(step)


def _edges(field: dict[str, Any]) -> str | None:
    """The `edges` of the GeoArrow extension metadata, or `None`."""
    text = _metadata(field).get("ARROW:extension:metadata")
    if text is None:
        return None
    try:
        value = json.loads(text)
    except ValueError:
        return "unreadable"
    return value.get("edges") if isinstance(value, dict) else "unreadable"


class Rejection(NamedTuple):
    cls: str
    category: str
    rule: str


def step_rejection(table: dict[str, Any], step: dict[str, Any], kernels: set[str]) -> Rejection | None:
    """The single ordered evaluation of REJ-002 for one step: version,
    vocabulary and CRS of the input (after the acceptances of the step's
    profile), the CRS the operation must use, the step's declared limits,
    then the values it decodes."""
    seen = table
    version = arrow_data.version_verdict(table)
    if version is not None:
        # REJ-002: nothing of an unsupported version is interpreted.
        return Rejection("input", version.category, version.rule)
    if (step["component"], step["operation"]) == DATA_RUN:
        # GEO-000: the profile's acceptance (DT-ARROW-003) is never revoked.
        seen = _copy(table)
        complete_missing_geometry_keys(seen)
        assign_field_ids(seen)
    found = arrow_data.schema_verdict(seen)
    if found is not None:
        return Rejection("input", found.category, found.rule)
    geometry = _geometry(seen)
    if computes(step, kernels):
        declared = [field for field in geometry if _metadata(field)[GEOMETRY + "crs_resolution"] != "missing"]
        for field in declared:
            if _metadata(field).get(GEOMETRY + "axis_order") in NORTH_FIRST:
                return Rejection("crs", "crs", "DT-ARROW-004")
            try:
                computed = arrow_data.computation_verdict(field)
            except arrow_data.Undecidable:
                computed = arrow_data.Verdict("crs", "GEO-006")
            if computed is not None:
                return Rejection("crs", computed.category, computed.rule)
        # DT-ARROW-004: planar kernels refuse geography and non-planar edges
        # (support, after the CRS class: REJ-002).
        for field in geometry:
            if _metadata(field)[GEOMETRY + "spatial_semantics"] == "geography" or _edges(field) not in (None, "planar"):
                return Rejection("support", "unsupported", "DT-ARROW-004")
    # Validated by `step_errors` before any step is evaluated.
    limits = _params(step).get("limits", [])
    if not isinstance(limits, list):
        raise ValueError("limits not validated")
    if "one_geometry_field" in limits and len(geometry) > 1:
        return Rejection("support", "unsupported", "GEO-012")
    if "one_geometry_type" in limits and any(
        len(arrow_data._type_list(_metadata(field).get(GEOMETRY + "types")) or []) > 1 for field in geometry
    ):
        return Rejection("support", "unsupported", "GEO-010")
    if decodes(step, kernels):
        found = arrow_data.value_verdict(seen)
        if found is not None:
            return Rejection("input", found.category, found.rule)
    return None


# --- chains (INTEROP-002) ---------------------------------------------------------

Key = tuple[str, str, int]


def step_key(step: dict[str, Any]) -> Key:
    return (step["component"], step["operation"], step["version"])


def chain_errors(
    chain: list[dict[str, Any]],
    operations: dict[Key, dict[str, Any]],
    direct_edges: set[tuple[Key, Key]],
) -> list[str]:
    errors = []
    # Steps are named by position: an operation spelling is data of the vector.
    for position, step in enumerate(chain, start=1):
        if step_key(step) not in operations:
            errors.append(f"step {position} names an unknown operation")
        for name in step["transformations"]:
            owners = TRANSFORMATION_OWNERS[name]
            if owners is not None and (step["component"], step["operation"]) not in owners:
                errors.append(f"step {position} cannot declare {name} (INTEROP-003)")
        prefix = step.get("provider_prefix")
        if prefix is not None and prefix.startswith(RESERVED_PREFIXES):
            errors.append("a provider prefix is reserved for the shared vocabulary")
    if chain and chain[0].get("via") == "target":
        errors.append("the first step cannot read a target no step wrote")
    for position, (before, after) in enumerate(zip(chain, chain[1:]), start=1):
        if after.get("via") == "target":
            # A step that takes a table, then one of the same component that
            # delivers one: as the catalog declares them, not only as named.
            writer = operations.get(step_key(before))
            reader = operations.get(step_key(after))
            if (
                before["component"] != after["component"]
                or not before["operation"].endswith(".write")
                or not after["operation"].endswith(".read")
                or writer is None
                or reader is None
                or not _arrow(writer["input"])
                or not _arrow(reader["output"])
            ):
                errors.append(f"steps {position} -> {position + 1} are not a write then a read of one component")
            # The target is read in the format it was written: when either
            # step selects a format, both name the same one.
            elif (
                writer["input"]["contract"] in SINK_FORMAT_INPUTS
                or reader["input"]["contract"] in SOURCE_FORMAT_INPUTS
            ):
                # An unknown format is reported on its step.
                written, read = _format(before), _format(after)
                if not isinstance(written, str) or not isinstance(read, str) or written != read:
                    errors.append(
                        f"steps {position} -> {position + 1} read the target in another format "
                        "than the one written (INTEROP-002)"
                    )
        elif (step_key(before), step_key(after)) not in direct_edges:
            errors.append(f"steps {position} -> {position + 1} are not a direct edge of the matrix")
    return errors


def step_errors(
    chain: list[dict[str, Any]], operations: dict[Key, dict[str, Any]], kernels: set[str]
) -> list[str]:
    """INTEROP-002: every parameter the gate reads, validated before any
    step is evaluated. `params` is an open object in the schema, so each
    field read is checked here for its type and its closed values: an
    object; `limits` a list of known names; `format` a known format, named
    exactly where the input contract selects one; a `data.run` plan
    `identity` or a registered kernel (any other plan would make the step
    carry instead of compute, in silence: INTEROP-004). A vector with any of
    these errors is not evaluated further (`vector_errors`)."""
    errors = []
    for position, step in enumerate(chain, start=1):
        params = step.get("params", {})
        if not isinstance(params, dict):
            errors.append(f"step {position} params is not an object (INTEROP-002)")
            continue
        limits = params.get("limits", [])
        if not isinstance(limits, list) or not all(isinstance(limit, str) and limit in LIMITS for limit in limits):
            errors.append(f"step {position} names an unknown limit (INTEROP-002)")
        operation = operations.get(step_key(step))
        names_format = "format" in params
        if operation is not None:
            selects = operation["input"]["contract"] in SOURCE_FORMAT_INPUTS | SINK_FORMAT_INPUTS
            if names_format and not selects:
                errors.append(f"step {position} names a format its input contract does not select (INTEROP-002)")
            elif selects and not names_format:
                errors.append(f"step {position} names no format, which its input contract selects (INTEROP-002)")
            elif names_format and not _known_format(params["format"]):
                errors.append(f"step {position} names an unknown format (INTEROP-002)")
        elif names_format and not _known_format(params["format"]):
            errors.append(f"step {position} names an unknown format (INTEROP-002)")
        if (step["component"], step["operation"]) == DATA_RUN:
            plan = params.get("plan")
            if not isinstance(plan, str) or (plan != "identity" and plan not in kernels):
                errors.append(
                    f"step {position} names a plan that is neither identity nor a registered kernel (INTEROP-002)"
                )
    return errors


def _arrow(side: dict[str, Any]) -> bool:
    """A catalog input or output that carries an Arrow IPC table."""
    return ARROW_INTERCHANGE in side["interchange_contracts"] and bool(
        ARROW_MEDIA_TYPES & set(side["content_types"])
    )


def _names_ipc_format(step: dict[str, Any]) -> bool:
    value = _format(step)
    return isinstance(value, str) and value in IPC_FORMATS


def reads_arrow_ipc(step: dict[str, Any], operation: dict[str, Any]) -> bool:
    """INTEROP-002: the step takes the input table as Arrow IPC, either as its
    catalog input or as the source it reads: its catalog input contract
    selects a source format, the `format` is Arrow IPC and its catalog output
    delivers the table. The name of the operation proves nothing."""
    if _arrow(operation["input"]):
        return True
    return (
        operation["input"]["contract"] in SOURCE_FORMAT_INPUTS
        and _arrow(operation["output"])
        and _names_ipc_format(step)
    )


def delivers_arrow_ipc(step: dict[str, Any], operation: dict[str, Any]) -> bool:
    """INTEROP-002: the step delivers a table as its catalog output, or writes
    it as Arrow IPC: its catalog input contract selects a sink format and
    takes the table, and the `format` is Arrow IPC."""
    if _arrow(operation["output"]):
        return True
    return (
        operation["input"]["contract"] in SINK_FORMAT_INPUTS
        and _arrow(operation["input"])
        and _names_ipc_format(step)
    )


def end_errors(vector: dict[str, Any], operations: dict[Key, dict[str, Any]]) -> list[str]:
    """INTEROP-002 at the ends of a chain: consecutive edges prove neither the
    first input nor the last output. A source vector reads a document, not
    the input table."""
    chain = vector["chain"]
    if vector["kind"] == "source" or not chain:
        return []
    errors = []
    first = operations.get(step_key(chain[0]))
    if first is not None and not reads_arrow_ipc(chain[0], first):
        errors.append("the first step does not read the input table as Arrow IPC (INTEROP-002)")
    last = operations.get(step_key(chain[-1]))
    if vector["kind"] == "handoff" and last is not None and not delivers_arrow_ipc(chain[-1], last):
        errors.append("the last step neither delivers a table nor writes it as Arrow IPC (INTEROP-002)")
    return errors


# --- rejections (INTEROP-004) -------------------------------------------------------

def rejection_errors(vector: dict[str, Any], table: dict[str, Any], kernels: set[str]) -> list[str]:
    expected = vector["expected_error"]
    step = vector["chain"][0]
    found = step_rejection(table, step, kernels)
    if found is None:
        return ["the step accepts the input under REJ-002"]
    errors = []
    if expected["class"] != found.cls:
        errors.append(f"expects class {expected['class']}, REJ-002 gives {found.cls}")
    if expected["category"] != found.category:
        errors.append(f"expects {expected['category']}, REJ-002 gives {found.category}")
    if found.rule not in expected["rules"]:
        errors.append(f"does not cite {found.rule}, the rule that decides")
    if found.cls != "input" and expected["category"] != CLASS_CATEGORY[found.cls]:
        errors.append(f"class {found.cls} is {CLASS_CATEGORY[found.cls]} (REJ-001)")
    if found.rule in VALUE_RULES:
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


# --- sources (GEO-002, GEO-003) --------------------------------------------------

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


POINT_WKT = re.compile(r"POINT \(([-+0-9.eE]+) ([-+0-9.eE]+)\)")


def wkt_csv_coordinates(text: str) -> list[list[float]]:
    """The points of the `wkt` column of a CSV document, as stored."""
    coordinates = []
    for row in csv.DictReader(io.StringIO(text)):
        match = POINT_WKT.fullmatch(row.get("wkt") or "")
        if match is None:
            raise ValueError("only two-dimensional WKT points are read here")
        coordinates.append([float(match.group(1)), float(match.group(2))])
    return coordinates


def source_errors(vector: dict[str, Any]) -> list[str]:
    expected = vector["expected_geometry"]
    source = vector["source"]
    step = vector["chain"][0]
    params = _params(step)
    errors = []
    # INTEROP-001: the parser is chosen by the format of the source document,
    # and the read request names that same format, never left implicit.
    if params.get("format") != source["format"]:
        errors.append("the read request does not name the format of the source document (INTEROP-001)")
    try:
        if source["format"] == "geojson":
            found = geojson_coordinates(source["text"])
        else:
            found = wkt_csv_coordinates(source["text"])
    except (ValueError, KeyError, TypeError):
        return ["source is not readable"]
    if source["format"] == "geojson":
        # RFC 7946: WGS 84, longitude then latitude, whatever any crs member says.
        if expected["crs_id"] != "OGC:CRS84":
            errors.append("a GeoJSON source declares OGC:CRS84 (RFC 7946)")
        if expected["axis_order"] != "lon_lat":
            errors.append("a GeoJSON source stores longitude first (GEO-002)")
        if not any(abs(x) > 90 for x, _ in found):
            errors.append("no longitude beyond 90 degrees: an exchanged order would pass unnoticed (GEO-003)")
    else:
        # GEO-002: a CSV fixes no order; the read request states it.
        if params.get("crs_id") != expected["crs_id"] or params.get("axis_order") != expected["axis_order"]:
            errors.append("a CSV source declares the CRS and order its read request states (GEO-002)")
        if not UTM.fullmatch(expected["crs_id"]) or expected["axis_order"] != "easting_northing":
            errors.append("the CSV vectors use a UTM CRS stored easting first")
        elif not any(y > 1_000_000 for _, y in found):
            errors.append("no northing beyond the range of eastings: an exchange would pass unnoticed (GEO-003)")
    if found != [[float(x), float(y)] for x, y in expected["coordinates"]]:
        errors.append("expected coordinates differ from the stored ones")
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
    parameters = step_errors(vector["chain"], operations, kernels)
    errors = chain_errors(vector["chain"], operations, direct_edges) + parameters + end_errors(vector, operations)
    if parameters:
        # A step with an invalid parameter is never evaluated: the steps
        # read only validated values.
        return errors
    if vector["kind"] == "source":
        return errors + source_errors(vector)
    input_path = (path.parent / vector["input"]).resolve()
    if not input_path.exists():
        return errors + ["the input does not exist"]
    table = load(input_path)
    try:
        if vector["kind"] == "rejection":
            return errors + rejection_errors(vector, table, kernels)
        current = _copy(table)
        for position, step in enumerate(vector["chain"]):
            found = step_rejection(current, step, kernels)
            if found is not None:
                return errors + [f"step {position + 1} rejects its input with {found.rule}"]
            apply(current, step)
    except arrow_data.FixtureError:
        # Its own gate reports the input; here it cannot be an input.
        return errors + ["the input is not a buildable table"]
    except ValueError:
        return errors + ["transformations cannot apply"]
    expected = expected_output(table, vector["chain"])
    errors += output_errors(vector, table, expected)
    if vector.get("contract") == "plenora-interop-assignment-vector-v1":
        errors += surface_output_errors(vector, table, vector["surface_outputs"])
    return errors
