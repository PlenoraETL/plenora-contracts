from __future__ import annotations

import importlib.util
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = ROOT / "conformance" / "row_diagnostics.py"
EXPECTED_CAMPAIGN = {
    "schema_version": 1,
    "campaign_id": "row-diagnostics-v1",
    "contract": "plenora-row-diagnostics-v1",
}


def _load_validator():
    spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("row diagnostics validator is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_report


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def judge_campaign(campaign: object, observations: object) -> dict[str, object]:
    manifest = _mapping(campaign, "campaign")
    mismatches = {
        field: manifest.get(field)
        for field, expected in EXPECTED_CAMPAIGN.items()
        if manifest.get(field) != expected
    }
    if mismatches:
        raise ValueError(f"unsupported campaign identity or version: {mismatches!r}")
    declared = _sequence(manifest.get("cases"), "campaign.cases")
    observed = _sequence(observations, "observations")
    declared_ids: set[object] = set()
    for raw in declared:
        identifier = _mapping(raw, "campaign case").get("id")
        if identifier in declared_ids:
            raise ValueError(f"duplicate declared case id: {identifier}")
        declared_ids.add(identifier)
    observed_by_id: dict[object, Mapping[str, Any]] = {}
    for raw in observed:
        entry = _mapping(raw, "observation")
        identifier = entry.get("id")
        if identifier in observed_by_id:
            raise ValueError(f"duplicate observation id: {identifier!r}")
        observed_by_id[identifier] = entry
    validate_report = _load_validator()
    reports: list[dict[str, object]] = []
    issues: list[str] = []

    for raw_case in declared:
        case = _mapping(raw_case, "case")
        case_id = case.get("id")
        event = observed_by_id.get(case_id)
        case_issues: list[str] = []
        if event is None:
            case_issues.append("missing observation")
        else:
            diagnostics = event.get("diagnostics")
            try:
                validate_report(_mapping(diagnostics, "observation.diagnostics"))
            except (TypeError, ValueError) as exc:
                case_issues.append(f"invalid diagnostics: {exc}")
            if event.get("exit_code") in (None, 0) or type(event.get("exit_code")) is not int:
                case_issues.append("operation did not fail closed")
            if event.get("output_exists") is not False:
                case_issues.append("partial output exists or is unknowable")
            if event.get("error_axes") != case.get("expected_error_axes"):
                case_issues.append("error axes mismatch")
            if diagnostics != case.get("expected_diagnostics"):
                case_issues.append("row diagnostics mismatch")
        reports.append(
            {
                "id": case_id,
                "status": "fail" if case_issues else "pass",
                "issues": case_issues,
            }
        )
        issues.extend(f"{case_id}: {issue}" for issue in case_issues)

    declared_ids = {case.get("id") for case in map(lambda raw: _mapping(raw, "case"), declared)}
    extra = sorted(identifier for identifier in observed_by_id if identifier not in declared_ids)
    if extra:
        issues.append(f"undeclared observations: {extra!r}")

    return {
        "schema_version": 1,
        "campaign_id": manifest.get("campaign_id"),
        "status": "fail" if issues else "pass",
        "cases": reports,
        "issues": issues,
    }
