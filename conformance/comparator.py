#!/usr/bin/env python3
"""Neutral, symmetric Arrow IPC comparator for conformance evidence."""

from __future__ import annotations

import base64
import datetime as dt
import decimal
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.ipc as ipc


POLICY_KEYS = {"artifact_byte", "batch_structure", "contract", "values"}


class ComparisonError(ValueError):
    """The requested comparison cannot be judged safely."""


def _display_bytes(value: bytes) -> str:
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeError:
        return "base64:" + base64.b64encode(value).decode("ascii")


def _metadata(metadata: dict[bytes, bytes] | None) -> dict[str, str]:
    return {
        _display_bytes(key): _display_bytes(value)
        for key, value in sorted((metadata or {}).items())
    }


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _logical_value(value: object) -> object:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return {"number": [value, 1]}
    if isinstance(value, float):
        if math.isnan(value):
            return {"float": "nan"}
        if math.isinf(value):
            return {"float": "infinity" if value > 0 else "-infinity"}
        numerator, denominator = value.as_integer_ratio()
        return {"number": [numerator, denominator]}
    if isinstance(value, decimal.Decimal):
        fraction = Fraction(value)
        return {"number": [fraction.numerator, fraction.denominator]}
    if isinstance(value, bytes):
        return {"bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return {type(value).__name__: value.isoformat()}
    if isinstance(value, dt.timedelta):
        return {"timedelta_microseconds": value // dt.timedelta(microseconds=1)}
    if isinstance(value, dict):
        return {
            str(key): _logical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_logical_value(item) for item in value]
    return {"python": type(value).__qualname__, "repr": repr(value)}


def _value_digest(table: pa.Table) -> str:
    payload = _logical_value(table.to_pylist())
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _child_fields(data_type: pa.DataType) -> list[pa.Field]:
    if pa.types.is_struct(data_type) or pa.types.is_union(data_type):
        return list(data_type)
    if (
        pa.types.is_list(data_type)
        or pa.types.is_large_list(data_type)
        or pa.types.is_fixed_size_list(data_type)
    ):
        return [data_type.value_field]
    if pa.types.is_map(data_type):
        return [data_type.key_field, data_type.item_field]
    return []


def _difference(
    category: str,
    path: str,
    before: object,
    after: object,
) -> dict[str, object]:
    return {
        "category": category,
        "path": path,
        "before": before,
        "after": after,
    }


def _diff_mapping(
    category: str,
    path: str,
    before: dict[str, str],
    after: dict[str, str],
) -> list[dict[str, object]]:
    differences: list[dict[str, object]] = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            differences.append(
                _difference(
                    category,
                    f"{path}[{key!r}]",
                    before.get(key),
                    after.get(key),
                )
            )
    return differences


def _contract_differences(
    before: pa.Schema, after: pa.Schema
) -> list[dict[str, object]]:
    differences = _diff_mapping(
        "contract",
        "schema.metadata",
        _metadata(before.metadata),
        _metadata(after.metadata),
    )
    if len(before) != len(after):
        differences.append(
            _difference("contract", "fields.count", len(before), len(after))
        )

    for index in range(max(len(before), len(after))):
        if index >= len(before):
            differences.append(
                _difference("contract", f"fields[{index}]", None, "added")
            )
            continue
        if index >= len(after):
            differences.append(
                _difference("contract", f"fields[{index}]", "removed", None)
            )
            continue

        differences.extend(
            _field_differences(before[index], after[index], f"fields[{index}]")
        )

    return differences


def _field_differences(
    before: pa.Field,
    after: pa.Field,
    path: str,
) -> list[dict[str, object]]:
    differences: list[dict[str, object]] = []
    for property_name, before_value, after_value in (
        ("name", before.name, after.name),
        ("type", str(before.type), str(after.type)),
        ("nullable", before.nullable, after.nullable),
    ):
        if before_value != after_value:
            differences.append(
                _difference(
                    "contract",
                    f"{path}.{property_name}",
                    before_value,
                    after_value,
                )
            )
    differences.extend(
        _diff_mapping(
            "contract",
            f"{path}.metadata",
            _metadata(before.metadata),
            _metadata(after.metadata),
        )
    )
    before_children = _child_fields(before.type)
    after_children = _child_fields(after.type)
    if len(before_children) != len(after_children):
        differences.append(
            _difference(
                "contract",
                f"{path}.children.count",
                len(before_children),
                len(after_children),
            )
        )
    for index, (before_child, after_child) in enumerate(
        zip(before_children, after_children)
    ):
        differences.extend(
            _field_differences(
                before_child,
                after_child,
                f"{path}.children[{index}]",
            )
        )
    return differences


def _read_ipc(path: Path) -> tuple[pa.Table, list[int]]:
    try:
        with ipc.open_file(path) as reader:
            batch_rows = [reader.get_batch(index).num_rows for index in range(reader.num_record_batches)]
            table = reader.read_all()
    except (OSError, pa.ArrowException) as exc:
        raise ComparisonError(f"cannot read Arrow IPC file {path}: {exc}") from exc
    return table, batch_rows


def compare_ipc(
    before_path: Path,
    after_path: Path,
    policy: dict[str, bool],
) -> dict[str, Any]:
    if set(policy) != POLICY_KEYS or any(
        not isinstance(policy[key], bool) for key in POLICY_KEYS if key in policy
    ):
        raise ComparisonError(
            f"policy must contain exactly boolean keys {sorted(POLICY_KEYS)!r}"
        )

    before = Path(before_path)
    after = Path(after_path)
    before_table, before_batches = _read_ipc(before)
    after_table, after_batches = _read_ipc(after)
    before_artifact = _file_digest(before)
    after_artifact = _file_digest(after)
    before_values = _value_digest(before_table)
    after_values = _value_digest(after_table)

    differences: list[dict[str, object]] = []
    if policy["artifact_byte"] and before_artifact != after_artifact:
        differences.append(
            _difference(
                "artifact_byte", "artifact.sha256", before_artifact, after_artifact
            )
        )
    if policy["batch_structure"] and before_batches != after_batches:
        differences.append(
            _difference(
                "batch_structure", "batches.rows", before_batches, after_batches
            )
        )
    if policy["contract"]:
        differences.extend(_contract_differences(before_table.schema, after_table.schema))
    before_logical = _logical_value(before_table.to_pylist())
    after_logical = _logical_value(after_table.to_pylist())
    if policy["values"] and before_logical != after_logical:
        differences.append(
            _difference("values", "values.sha256", before_values, after_values)
        )

    return {
        "status": "fail" if differences else "pass",
        "policy": dict(sorted(policy.items())),
        "before": {
            "path": str(before),
            "artifact_sha256": before_artifact,
            "values_sha256": before_values,
            "rows": before_table.num_rows,
            "columns": before_table.num_columns,
            "batch_rows": before_batches,
        },
        "after": {
            "path": str(after),
            "artifact_sha256": after_artifact,
            "values_sha256": after_values,
            "rows": after_table.num_rows,
            "columns": after_table.num_columns,
            "batch_rows": after_batches,
        },
        "differences": differences,
    }
