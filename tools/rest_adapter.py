"""Reference REST-to-Arrow adapter (REST-to-Arrow Adapter 1.0, RA-002 to RA-010).

It converts a REST execution result with a declaration and returns the whole
outcome a vector states: the Arrow schema, the rows, the row diagnostics and
the REST status of a table, or every axis of an error. The validator
compares the outcome with the one each vector states, so a vector cannot
claim an outcome the rules do not give. It is a reference for the vectors,
not a component.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any

from json_values import same_value

INT64 = 2**63
# Matched with `fullmatch`: `$` would admit a final line feed.
ARRAY_INDEX = re.compile(r"0|[1-9][0-9]*")
POINTER = re.compile(r"(/([^~/]|~[01])*)+")
# RA-006: an undeclared member is never named; its key is source data.
UNDECLARED = "@undeclared"
EXAMPLES_LIMIT = 128
# RA-008: the phase of each error category; every error has remote effect
# `none` and retry `never`.
PHASES = {
    "invalid_configuration": "validate",
    "execution": "validate",
    "schema": "validate",
    "data_mapping": "read",
}


class RecordError(Exception):
    def __init__(self, cause: str) -> None:
        super().__init__(cause)
        self.cause = cause


def error(category: str, **context: Any) -> dict[str, Any]:
    found = {
        "outcome": "error",
        "category": category,
        "phase": PHASES[category],
        "remote_effect": "none",
        "retry": "never",
    }
    found.update(context)
    return found


def tokens(pointer: str) -> list[str]:
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer.split("/")[1:]]


MISSING = object()


def evaluate(record: Any, pointer: str) -> Any:
    """RFC 6901 evaluation; `MISSING` for an absent member or index."""
    value = record
    for token in tokens(pointer):
        if isinstance(value, dict):
            if token not in value:
                return MISSING
            value = value[token]
        elif isinstance(value, list):
            if not ARRAY_INDEX.fullmatch(token):
                raise RecordError("adapter.path_not_traversable")
            index = int(token)
            if index >= len(value):
                return MISSING
            value = value[index]
        else:
            raise RecordError("adapter.path_not_traversable")
    return value


def convert(value: Any, kind: str, nullable: bool) -> Any:
    if value is MISSING or value is None:
        if not nullable:
            raise RecordError("adapter.null_in_non_nullable")
        return None
    if kind == "bool":
        if isinstance(value, bool):
            return value
    elif kind == "int64":
        # The exact integer of the literal, never through binary64.
        # An integer literal is an `int` (`-0` included, the integer 0);
        # the value is the plain integer, never the literal's text.
        if isinstance(value, int) and not isinstance(value, bool):
            if not -INT64 <= value < INT64:
                raise RecordError("adapter.not_representable")
            return int(value)
    elif kind == "float64":
        # A decimal is the exact number the parser read (`JsonNumber`); its
        # nearest binary64 is the one a float parse would give.
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            try:
                converted = float(value)
            except OverflowError as overflow:
                raise RecordError("adapter.not_representable") from overflow
            if math.isinf(converted) or math.isnan(converted):
                raise RecordError("adapter.not_representable")
            return converted
    elif isinstance(value, str):
        return value
    raise RecordError("adapter.type_mismatch")


def declaration_errors(declaration: dict[str, Any]) -> list[str]:
    fields = declaration["fields"]
    names = [field["name"] for field in fields]
    identities = [field["field_id"] for field in fields]
    errors = []
    if "failed" in declaration["accept_status"]:
        errors.append("accept_status lists failed")
    if len(names) != len(set(names)):
        errors.append("repeated field name")
    if UNDECLARED in names:
        errors.append("a field uses the reserved name @undeclared")
    if len(identities) != len(set(identities)):
        errors.append("repeated field identifier")
    for position, field in enumerate(fields):
        # RA-003: an integer literal. JSON Schema's `integer` also admits
        # `123.0` and `1.23e2`, which are not decimal integers as text
        # (ARROW-003) and which an int64 value refuses too (RA-005).
        identity = field["field_id"]
        if not _integer_literal(identity) or identity < 0:
            errors.append(f"field identifier of field #{position} is not a non-negative integer")
        if not POINTER.fullmatch(field["pointer"]):
            # By position: a field name is the declaration's data (ERR-010).
            errors.append(f"pointer of field #{position} is not RFC 6901")
    return errors


def _integer_literal(value: Any) -> bool:
    """A JSON number written without fraction or exponent: the parser gives
    an `int` exactly then (and `bool` is not one)."""
    return isinstance(value, int) and not isinstance(value, bool)


def field_id_text(value: Any) -> str:
    """ARROW-003: the decimal text of an identity, never `str` of a JSON
    number, which writes `123.0` for a float."""
    if not _integer_literal(value) or value < 0:
        raise ValueError("a field identity is a non-negative integer")
    # The integer's decimal text: `-0` is the identity 0.
    return str(int(value))


def arrow_schema(declaration: dict[str, Any]) -> dict[str, Any]:
    """RA-010: the declared schema, whatever the records."""
    return {
        "schema_metadata": {"plenora.contract.version": "1"},
        "fields": [
            {
                "name": field["name"],
                "type": field["type"],
                "nullable": field["nullable"],
                "metadata": {"plenora.field_id": field_id_text(field["field_id"])},
            }
            for field in declaration["fields"]
        ],
    }


def diagnostics(excluded: list[dict[str, Any]], records: int) -> dict[str, Any]:
    """RA-007: the row diagnostics of the excluded records."""
    counts: dict[str, int] = {}
    for item in excluded:
        counts[item["cause"]] = counts.get(item["cause"], 0) + 1
    examples = []
    for item in excluded[:EXAMPLES_LIMIT]:
        example = {"source_index": item["record"], "cause": item["cause"]}
        if item["cause"] != "adapter.undeclared_member":
            example["column"] = item["field"]
        examples.append(example)
    return {
        "contract": "plenora-row-diagnostics-v1",
        "scope": "read",
        "index_basis": "source_row_zero_based",
        "completeness": "complete",
        "observed_total": len(excluded),
        "input_total": records,
        "counts": counts,
        "examples_limit": EXAMPLES_LIMIT,
        "examples_truncated": len(excluded) > EXAMPLES_LIMIT,
        "examples": examples,
    }


def adapt(declaration: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if declaration_errors(declaration):
        return error("invalid_configuration")
    if result["status"] not in declaration["accept_status"]:
        return error("execution")
    output = result["output"]
    if output.get("type") != "records" or not isinstance(output.get("records"), list):
        return error("schema")
    fields = declaration["fields"]
    declared_heads = {tokens(field["pointer"])[0] for field in fields}
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for index, record in enumerate(output["records"]):
        row: dict[str, Any] = {}
        failure: tuple[str, str] | None = None
        for field in fields:
            try:
                row[field["name"]] = convert(
                    evaluate(record, field["pointer"]), field["type"], field["nullable"]
                )
            except RecordError as problem:
                failure = (field["name"], problem.cause)
                break
        if failure is None and declaration["undeclared_members"] == "reject" and isinstance(record, dict):
            if any(name not in declared_heads for name in record):
                failure = (UNDECLARED, "adapter.undeclared_member")
        if failure is not None:
            if declaration["on_record_error"] == "fail":
                return error("data_mapping", record=index, field=failure[0], cause=failure[1])
            excluded.append({"record": index, "field": failure[0], "cause": failure[1]})
            continue
        rows.append(row)
    return {
        "outcome": "table",
        "schema": arrow_schema(declaration),
        "rows": rows,
        "diagnostics": diagnostics(excluded, len(output["records"]))
        if declaration["on_record_error"] == "exclude" else None,
        "rest_status": result["status"],
        "rest_errors": len(result["errors"]),
    }


def _same(left: Any, right: Any) -> bool:
    """Equality that tells 1 from 1.0, True from 1 and 0.0 from -0.0, by type
    and value at every depth, walked without recursion (`json_values`)."""
    # VALUE: the outcome against the vector's expectation; a float by
    # `repr`, so the sign of a zero counts (RA-003), `-0` is the integer 0.
    return same_value(left, right)


def vector_errors(vector: dict[str, Any]) -> list[str]:
    found = adapt(vector["declaration"], vector["result"])
    expected = vector["expect"]
    # A float64 written as an integer literal in the vector is the same value.
    if expected.get("outcome") == "table" and found["outcome"] == "table":
        kinds = {field["name"]: field["type"] for field in vector["declaration"]["fields"]}
        expected = dict(expected)
        expected["rows"] = [
            {
                name: float(value) if kinds.get(name) == "float64" and isinstance(value, (int, Decimal))
                and not isinstance(value, bool) else value
                for name, value in row.items()
            }
            for row in expected["rows"]
        ]
    if not _same(found, expected):
        # The path of the first difference, never the outcomes: they hold
        # source values and keys (ERR-010).
        return [f"expect differs from the outcome the rules give at {difference(expected, found)}"]
    return []


# Keys of the outcome's own structure; any other key (a field name, a cause,
# a metadata key) may be data and is never written into a message.
STRUCTURAL_KEYS = {
    "outcome", "schema", "schema_metadata", "fields", "rows", "diagnostics", "rest_status",
    "rest_errors", "category", "phase", "remote_effect", "retry", "record", "field", "cause",
    "name", "type", "nullable", "metadata", "contract", "scope", "index_basis", "completeness",
    "observed_total", "input_total", "counts", "examples_limit", "examples_truncated", "examples",
    "source_index", "column",
}


def _segment(key: Any, position: int, structural: bool) -> str:
    return str(key) if structural and key in STRUCTURAL_KEYS else f"#{position}"


_MISSING = object()
_MAPS = ("counts", "metadata", "schema_metadata")


def _member_tasks(left: dict, right: dict, structural: bool, inner: bool):
    """The members of two objects in sorted-key order, as `(segment, left,
    right, structural)`; a key present in one only yields `_MISSING`."""
    for position, key in enumerate(sorted(set(left) | set(right), key=str)):
        segment = _segment(key, position, inner)
        if key not in left or key not in right:
            yield (segment, _MISSING, None, None)
            return
        yield (segment, left[key], right[key], structural)


def _element_tasks(left: list, right: list):
    """The elements of two arrays of one length, in order. An array element
    is named, and its structure judged, as the recursion did."""
    for index, (one, other) in enumerate(zip(left, right)):
        yield (str(index), one, other, True)


def difference(left: Any, right: Any, path: str = "", structural: bool = True) -> str:
    """The path of the first difference of two values that are not `_same`.
    Inside a row, a count map or a metadata map, a member is named by its
    position among the sorted keys, never by its key. One depth-first walk
    in document order, with an explicit stack: linear in time (no subtree is
    compared twice) and in memory, the path being one shared list of
    segments (`trail`) joined only for the answer, never a string copied at
    every level."""
    root_rows = "/rows/" in path + "/"
    root_last = path.rsplit("/", 1)[-1] if path else ""
    trail: list[str] = []
    rows = 0

    def where() -> str:
        return path + "".join("/" + segment for segment in trail)

    def expand(one: Any, other: Any, flag: bool) -> str | None:
        """Push the children of a node, or answer when the node differs."""
        if type(one) is type(other) and isinstance(one, dict):
            last = trail[-1] if trail else root_last
            inner = flag and last not in _MAPS and not rows and not root_rows
            frames.append(_member_tasks(one, other, flag, inner))
            trail.append("")
            return None
        if type(one) is type(other) and isinstance(one, list):
            if len(one) != len(other):
                return f"{where()} (length)"
            frames.append(_element_tasks(one, other))
            trail.append("")
            return None
        if not _same(one, other):
            return where() or "/"
        return None

    frames: list[Any] = []
    found = expand(left, right, structural)
    while found is None and frames:
        task = next(frames[-1], None)
        if task is None:
            frames.pop()
            rows -= trail.pop() == "rows"
            continue
        segment, one, other, flag = task
        rows += (segment == "rows") - (trail[-1] == "rows")
        trail[-1] = segment
        if one is _MISSING:
            return where()
        found = expand(one, other, flag)
    return found if found is not None else (path or "/")
