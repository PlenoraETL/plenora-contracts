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
from typing import Any

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
        if isinstance(value, int) and not isinstance(value, bool):
            if not -INT64 <= value < INT64:
                raise RecordError("adapter.not_representable")
            return value
    elif kind == "float64":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
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
    for field in fields:
        if not POINTER.fullmatch(field["pointer"]):
            errors.append(f"pointer of {field['name']} is not RFC 6901")
    return errors


def arrow_schema(declaration: dict[str, Any]) -> dict[str, Any]:
    """RA-010: the declared schema, whatever the records."""
    return {
        "schema_metadata": {"plenora.contract.version": "1"},
        "fields": [
            {
                "name": field["name"],
                "type": field["type"],
                "nullable": field["nullable"],
                "metadata": {"plenora.field_id": str(field["field_id"])},
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
    """Equality that tells 1 from 1.0, True from 1 and 0.0 from -0.0."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(map(_same, left, right))
    if isinstance(left, float):
        return left == right and math.copysign(1.0, left) == math.copysign(1.0, right)
    return left == right


def vector_errors(vector: dict[str, Any]) -> list[str]:
    found = adapt(vector["declaration"], vector["result"])
    expected = vector["expect"]
    # A float64 written as an integer literal in the vector is the same value.
    if expected.get("outcome") == "table" and found["outcome"] == "table":
        kinds = {field["name"]: field["type"] for field in vector["declaration"]["fields"]}
        expected = dict(expected)
        expected["rows"] = [
            {
                name: float(value) if kinds.get(name) == "float64" and isinstance(value, int)
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


def difference(left: Any, right: Any, path: str = "", structural: bool = True) -> str:
    """The path of the first difference of two values that are not `_same`.
    Inside a row, a count map or a metadata map, a member is named by its
    position among the sorted keys, never by its key."""
    if type(left) is type(right) and isinstance(left, dict):
        inner = structural and not path.endswith(("/counts", "/metadata", "/schema_metadata")) \
            and "/rows/" not in path + "/"
        keys = sorted(set(left) | set(right), key=str)
        for position, key in enumerate(keys):
            segment = _segment(key, position, inner)
            if key not in left or key not in right:
                return f"{path}/{segment}"
            if not _same(left[key], right[key]):
                return difference(left[key], right[key], f"{path}/{segment}", structural)
    if type(left) is type(right) and isinstance(left, list):
        if len(left) != len(right):
            return f"{path} (length)"
        for index, (one, other) in enumerate(zip(left, right)):
            if not _same(one, other):
                return difference(one, other, f"{path}/{index}")
    return path or "/"
