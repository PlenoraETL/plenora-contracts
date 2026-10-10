"""Reference REST-to-Arrow adapter (REST-to-Arrow Adapter 1.0, RA-002 to RA-009).

It converts a REST execution result with a declaration and returns either
the table (rows as JSON values, the excluded records and the REST status) or
the error. The validator compares the outcome with the one each vector
states, so a vector cannot claim an outcome the rules do not give. It is a
reference for the vectors, not a component.
"""

from __future__ import annotations

import math
import re
from typing import Any, NamedTuple

INT64 = 2**63
ARRAY_INDEX = re.compile(r"^(0|[1-9][0-9]*)$")
POINTER = re.compile(r"^(/([^~/]|~[01])*)+$")


class RecordError(Exception):
    def __init__(self, cause: str) -> None:
        super().__init__(cause)
        self.cause = cause


class Outcome(NamedTuple):
    outcome: str
    rows: list[dict[str, Any]] | None = None
    excluded: list[dict[str, Any]] | None = None
    rest_status: str | None = None
    rest_errors: int | None = None
    category: str | None = None
    record: int | None = None
    field: str | None = None
    cause: str | None = None

    def as_expect(self) -> dict[str, Any]:
        if self.outcome == "table":
            return {
                "outcome": "table",
                "rows": self.rows,
                "excluded": self.excluded,
                "rest_status": self.rest_status,
                "rest_errors": self.rest_errors,
            }
        found = {"outcome": "error", "category": self.category}
        for key in ("record", "field", "cause"):
            if getattr(self, key) is not None:
                found[key] = getattr(self, key)
        return found


def error(category: str, **context: Any) -> Outcome:
    return Outcome("error", category=category, **context)


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
            if not ARRAY_INDEX.match(token):
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
    if len(names) != len(set(names)):
        errors.append("repeated field name")
    if len(identities) != len(set(identities)):
        errors.append("repeated field identifier")
    for field in fields:
        if not POINTER.match(field["pointer"]):
            errors.append(f"pointer of {field['name']} is not RFC 6901")
    return errors


def adapt(declaration: dict[str, Any], result: dict[str, Any]) -> Outcome:
    if declaration_errors(declaration):
        return error("invalid_configuration")
    output = result["output"]
    if output.get("type") != "records" or not isinstance(output.get("records"), list):
        return error("schema")
    if result["status"] not in declaration["accept_status"]:
        return error("execution")
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
            extra = [name for name in record if name not in declared_heads]
            if extra:
                failure = (extra[0], "adapter.undeclared_member")
        if failure is not None:
            if declaration["on_record_error"] == "fail":
                return error("data_mapping", record=index, field=failure[0], cause=failure[1])
            excluded.append({"record": index, "field": failure[0], "cause": failure[1]})
            continue
        rows.append(row)
    return Outcome(
        "table",
        rows=rows,
        excluded=excluded,
        rest_status=result["status"],
        rest_errors=len(result["errors"]),
    )


def _same(left: Any, right: Any) -> bool:
    """Equality that tells 1 from 1.0 and True from 1."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(map(_same, left, right))
    return left == right


def vector_errors(vector: dict[str, Any]) -> list[str]:
    found = adapt(vector["declaration"], vector["result"]).as_expect()
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
        return [f"states {vector['expect']}, the rules give {found}"]
    return []
