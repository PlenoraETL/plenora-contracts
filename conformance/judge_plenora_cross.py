#!/usr/bin/env python3
"""Judge read-only Plenora/Data parity without treating either as the oracle."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pyarrow.ipc as ipc
from shapely import wkb

if __package__:
    from .comparator import compare_ipc
else:
    from comparator import compare_ipc


LOGICAL_POLICY = {
    "artifact_byte": False,
    "batch_structure": False,
    "contract": False,
    "values": True,
}
CONTRACT_POLICY = {
    "artifact_byte": False,
    "batch_structure": False,
    "contract": True,
    "values": False,
}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _difference_matches(
    difference: dict[str, Any], declaration: dict[str, Any]
) -> bool:
    for key in ("category", "path"):
        if difference.get(key) != declaration.get(key):
            return False
    for side in ("before", "after"):
        presence_key = f"{side}_presence"
        if presence_key in declaration:
            expected_presence = declaration[presence_key]
            observed_presence = "present" if difference.get(side) is not None else "absent"
            if observed_presence != expected_presence:
                return False
        elif difference.get(side) != declaration.get(side):
            return False
    return True


def _undeclared_differences(
    differences: list[dict[str, Any]], declarations: list[object]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    remaining = list(differences)
    missing: list[dict[str, Any]] = []
    for raw in declarations:
        declaration = _mapping(raw, "allowed contract difference")
        match = next(
            (row for row in remaining if _difference_matches(row, declaration)), None
        )
        if match is None:
            missing.append(declaration)
        else:
            remaining.remove(match)
    return remaining, missing


def build_report(spec: object, artifacts: Path) -> dict[str, Any]:
    campaign = _mapping(spec, "spec")
    root = Path(artifacts)
    required = {
        "plenora_filter": root / "plenora-filter.arrow",
        "data_filter": root / "data-filter.arrow",
        "plenora_reproject": root / "plenora-reproject.json",
        "data_reproject": root / "data-reproject.arrow",
    }
    missing_files = [str(path) for path in required.values() if not path.is_file()]
    if missing_files:
        raise ValueError(f"missing cross-comparison artifacts: {missing_files!r}")

    logical = compare_ipc(
        required["plenora_filter"], required["data_filter"], LOGICAL_POLICY
    )
    contract = compare_ipc(
        required["plenora_filter"], required["data_filter"], CONTRACT_POLICY
    )
    filter_spec = _mapping(campaign.get("filter"), "spec.filter")
    undeclared, missing_declarations = _undeclared_differences(
        contract["differences"], filter_spec.get("allowed_contract_differences") or []
    )

    plenora_document = json.loads(
        required["plenora_reproject"].read_text(encoding="utf-8")
    )
    plenora_geometry = _mapping(plenora_document, "plenora reproject artifact")
    with ipc.open_file(required["data_reproject"]) as reader:
        data_table = reader.read_all()
    geometry_field = data_table.schema.field("geometry")
    metadata = {
        key.decode("utf-8"): value.decode("utf-8")
        for key, value in (geometry_field.metadata or {}).items()
    }
    data_geometries = [wkb.loads(value.as_py()) for value in data_table["geometry"]]
    plenora_geometries = [
        wkb.loads(bytes.fromhex(_mapping(row, "Plenora geometry")["wkb_hex"]))
        for row in plenora_geometry.get("geometries") or []
    ]
    distances = [
        left.hausdorff_distance(right)
        for left, right in zip(plenora_geometries, data_geometries, strict=False)
    ]
    max_distance = max(distances, default=float("inf"))
    reproject_spec = _mapping(campaign.get("reproject"), "spec.reproject")
    expected_crs = reproject_spec.get("crs")
    tolerance = reproject_spec.get("hausdorff_tolerance_degrees")
    geometry_valid = all(
        geometry.is_valid for geometry in [*plenora_geometries, *data_geometries]
    )
    same_count = (
        plenora_geometry.get("rows")
        == len(plenora_geometries)
        == len(data_geometries)
        == data_table.num_rows
    )
    crs_pass = (
        plenora_geometry.get("crs") == expected_crs
        and metadata.get("plenora.geometry.crs_id") == expected_crs
        and metadata.get("plenora.geometry.srid") == expected_crs.removeprefix("EPSG:")
    )

    issues: list[str] = []
    if logical["status"] != "pass":
        issues.append("filter logical values differ")
    if undeclared:
        issues.append("undeclared filter contract differences")
    if missing_declarations:
        issues.append("declared filter contract differences were not observed")
    if not same_count:
        issues.append("reproject row or geometry count differs")
    if not geometry_valid:
        issues.append("invalid geometry observed")
    if not crs_pass:
        issues.append("reproject CRS differs")
    if not isinstance(tolerance, (int, float)) or max_distance > tolerance:
        issues.append("reproject Hausdorff tolerance exceeded")

    return {
        "schema_version": 1,
        "campaign_id": campaign.get("campaign_id"),
        "status": "fail" if issues else "pass_with_declared_differences",
        "reference_revisions": {
            "plenora": campaign.get("plenora_revision"),
            "data": campaign.get("data_revision"),
        },
        "filter": {
            "logical_values": logical["status"],
            "rows": logical["before"]["rows"],
            "observed_contract_differences": contract["differences"],
            "undeclared_contract_differences": undeclared,
            "missing_declared_differences": missing_declarations,
            "assessment": "data_preserves_narrower_physical_types",
        },
        "reproject": {
            "rows": len(data_geometries),
            "crs": expected_crs,
            "crs_judge": "pass" if crs_pass else "fail",
            "geometry_validity": "pass" if geometry_valid else "fail",
            "max_hausdorff_degrees": max_distance,
            "tolerance_degrees": tolerance,
            "status": (
                "pass"
                if same_count and geometry_valid and crs_pass and max_distance <= tolerance
                else "fail"
            ),
        },
        "scope_limits": [
            "read-only comparison",
            "table.filter and geo.reproject only",
            "does not establish persistence, provider, orchestration, or performance parity",
        ],
        "issues": issues,
    }


def _write_json_atomic(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = build_report(
        json.loads(arguments.spec.read_text(encoding="utf-8")), arguments.artifacts
    )
    _write_json_atomic(arguments.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "pass_with_declared_differences" else 1


if __name__ == "__main__":
    raise SystemExit(main())
