"""Verdicts of Arrow Primary Geometry 1.0 (PRIM-001 to PRIM-009).

The contract adds one schema metadata key, `plenora.primary_geometry`, to
the vocabulary that Arrow Geometry Semantics 1.0 reads. `verdict` is the
verdict of `arrow_data` with the key's checks placed in the vocabulary class
of REJ-002: after the checks of every field, so that a repeated field
identifier is reported first, and before the CRS class. `primary` gives the
state PRIM-002 reads from a valid schema, `canonical` the form PRIM-004
emits, `operands` the selection of PRIM-007 and `geoparquet_errors` the
correspondence of PRIM-008.

Messages name fields by position and rules by identifier, never a field
name, a key value or a row value (decision 0021).
"""

from __future__ import annotations

from typing import Any

import arrow_data
from arrow_data import Verdict

KEY = "plenora.primary_geometry"
NONE = "none"


def geometry_fields(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [field for field in table["fields"] if arrow_data.is_geometry(field)]


def key_verdict(table: dict[str, Any]) -> Verdict | None:
    """PRIM-001 and PRIM-003: the key, where it may stand and what it names,
    resolved against the schema as received."""
    if any(KEY in field["metadata"] for field in table["fields"]):
        # PRIM-001: a schema key, never a field key.
        return Verdict("schema", "PRIM-001")
    value = table["schema_metadata"].get(KEY)
    if value is None:
        return None
    if value != NONE and not arrow_data.DECIMAL.fullmatch(value):
        return Verdict("schema", "PRIM-001")
    if not geometry_fields(table):
        return Verdict("schema", "PRIM-003")
    if value == NONE:
        return None
    named = [field for field in table["fields"] if field["metadata"].get("plenora.field_id") == value]
    if len(named) != 1 or not arrow_data.is_geometry(named[0]):
        return Verdict("schema", "PRIM-003")
    return None


def schema_verdict(table: dict[str, Any], received: dict[str, Any] | None = None) -> Verdict | None:
    """REJ-002 up to the CRS class, with the key in the vocabulary class.

    `received` is the schema before a profile completed it (DT-ARROW-003):
    the key is resolved against what the producer sent (PRIM-003)."""
    return (
        arrow_data.version_verdict(table)
        or arrow_data._vocabulary(table["fields"])
        or key_verdict(received if received is not None else table)
        or arrow_data._crs(table["fields"])
    )


def verdict(table: dict[str, Any]) -> Verdict | None:
    """The first rejection a component that claims the contract reports."""
    return schema_verdict(table) or arrow_data.value_verdict(table)


def primary(table: dict[str, Any]) -> dict[str, Any] | None:
    """PRIM-002: the primary geometry field of a valid schema, or `None`."""
    geometry = geometry_fields(table)
    value = table["schema_metadata"].get(KEY)
    if value is None:
        return geometry[0] if len(geometry) == 1 else None
    if value == NONE:
        return None
    return next(field for field in geometry if field["metadata"].get("plenora.field_id") == value)


def canonical_value(table: dict[str, Any]) -> str | None:
    """PRIM-004: the key a component emits for the state of a valid schema;
    `None` when it omits the key."""
    geometry = geometry_fields(table)
    found = primary(table)
    if len(geometry) == 1 and found is None:
        return NONE
    if len(geometry) > 1 and found is not None:
        return found["metadata"]["plenora.field_id"]
    return None


def canonical(table: dict[str, Any]) -> None:
    """PRIM-004: rewrite the key of a valid schema in the emitted form."""
    value = canonical_value(table)
    if value is None:
        table["schema_metadata"].pop(KEY, None)
    else:
        table["schema_metadata"][KEY] = value


def operands(table: dict[str, Any], selection: str | None) -> list[dict[str, Any]] | Verdict:
    """PRIM-007: the geometry field an operation that computes with one
    geometry takes, by the identity the request selects or, without one, the
    primary; without either, the operation-schema rejection."""
    if selection is None:
        found = primary(table)
        return [found] if found is not None else Verdict("schema", "PRIM-007")
    named = [field for field in table["fields"] if field["metadata"].get("plenora.field_id") == selection]
    if len(named) != 1 or not arrow_data.is_geometry(named[0]):
        return Verdict("schema", "PRIM-007")
    return named


def vector_errors(vector: dict[str, Any]) -> list[str]:
    """Disagreements between a vector of `vectors/arrow-primary-v1` and the
    verdict the rules give (PRIM-009)."""
    try:
        found = verdict(vector)
    except arrow_data.FixtureError as error:
        return [f"is not a buildable table: {error}"]
    if vector["expect"] == "valid":
        if found is not None:
            return [f"must be accepted, but {found.rule} rejects it with {found.category}"]
        return arrow_data.computation_errors(vector)
    if found is None:
        return ["must be rejected, but every rule accepts it"]
    errors = []
    if vector["category"] != found.category:
        errors.append(f"states category {vector['category']}, the rules give {found.category}")
    if found.rule not in vector["rules"]:
        errors.append(f"does not cite {found.rule}, the rule that rejects it")
    return errors


# --- GeoParquet (PRIM-008) ------------------------------------------------------


def geoparquet_errors(vector: dict[str, Any], table: dict[str, Any]) -> list[str]:
    """PRIM-008: the `geo` metadata a writer emits for a table, or the table
    a reader delivers for a `geo` metadata. `table` is the Arrow side, a
    valid vector of the contract."""
    try:
        rejected = verdict(dict(table, expect="valid"))
    except arrow_data.FixtureError:
        return ["the table is not a buildable table"]
    if rejected is not None:
        return ["the table is not a valid table of the contract"]
    names = [field["name"] for field in geometry_fields(table)]
    found = primary(table)
    if vector["direction"] == "write":
        if found is None:
            # A table without a primary cannot be written: never one chosen.
            error = vector.get("expected_error")
            if error is None:
                return ["a table without a primary is written only as a rejection (PRIM-008)"]
            errors = []
            if error["category"] != "unsupported":
                errors.append("a table without a primary is unsupported by the format (PRIM-008)")
            if "PRIM-008" not in error["rules"]:
                errors.append("does not cite PRIM-008, the rule that rejects it")
            return errors
        if "expected_error" in vector:
            return ["a table with a primary is written, not rejected (PRIM-008)"]
        geo = vector["geo"]
        errors = []
        if geo["primary_column"] != found["name"]:
            errors.append("primary_column does not name the primary field (PRIM-008)")
        if geo["columns"] != names:
            errors.append("columns do not list every geometry field in field order (PRIM-008)")
        return errors
    geo = vector["geo"]
    errors = []
    if geo["columns"] != names:
        errors.append("the delivered geometry fields are not the columns of the file in their order (PRIM-008)")
    if found is None or found["name"] != geo["primary_column"]:
        errors.append("the delivered primary is not the field primary_column names (PRIM-008)")
    if table["schema_metadata"].get(KEY) != canonical_value(table):
        errors.append("the delivered key is not in the form PRIM-004 emits")
    return errors
