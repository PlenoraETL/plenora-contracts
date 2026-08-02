#!/usr/bin/env python3
"""Build fail-closed live PostgreSQL campaign evidence from retained artifacts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

if __package__:
    from .comparator import compare_ipc
    from .fidelity import judge_loss_counts, judge_transitions
else:
    from comparator import compare_ipc
    from fidelity import judge_loss_counts, judge_transitions


STRICT_POLICY = {
    "artifact_byte": True,
    "batch_structure": True,
    "contract": True,
    "values": True,
}
VALUES_POLICY = {
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


def _required_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _fault_report(
    required: list[object],
    observed: list[object],
) -> tuple[list[dict[str, Any]], list[str]]:
    observed_by_id = {
        row.get("id"): row for row in observed if isinstance(row, dict)
    }
    reports: list[dict[str, Any]] = []
    issues: list[str] = []
    for raw in required:
        expected = _required_mapping(raw, "fault case")
        identifier = expected.get("id")
        event = observed_by_id.get(identifier)
        passed = bool(
            event
            and event.get("exit_code") not in (None, 0)
            and event.get("category") == expected.get("required_category")
            and event.get("remote_effect") == expected.get("required_remote_effect")
            and (
                not expected.get("artifact_must_not_exist")
                or event.get("artifact_exists") is False
            )
        )
        report = {
            "id": identifier,
            "status": "pass" if passed else "fail",
            "category": event.get("category") if event else None,
            "remote_effect": event.get("remote_effect") if event else None,
            "partial_artifact": event.get("artifact_exists") if event else None,
        }
        reports.append(report)
        if not passed:
            issues.append(f"fault case {identifier!r} did not match its specification")
    extra = sorted(set(observed_by_id) - {row.get("id") for row in required if isinstance(row, dict)})
    if extra:
        issues.append(f"undeclared fault observations: {extra!r}")
    return reports, issues


def build_report(
    spec: object,
    events: object,
    artifacts: Path,
) -> dict[str, Any]:
    campaign = _required_mapping(spec, "spec")
    observation = _required_mapping(events, "events")
    root = Path(artifacts)
    paths = {
        name: root / filename
        for name, filename in {
            "postgres_1": "postgres-1.arrow",
            "postgres_2": "postgres-2.arrow",
            "data": "data.arrow",
            "io": "io.arrow",
        }.items()
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise ValueError(f"missing retained artifacts: {missing!r}")

    determinism = compare_ipc(paths["postgres_1"], paths["postgres_2"], STRICT_POLICY)
    database_to_data = compare_ipc(paths["postgres_1"], paths["data"], STRICT_POLICY)
    data_to_io_values = compare_ipc(paths["data"], paths["io"], VALUES_POLICY)
    data_to_io_contract = compare_ipc(paths["data"], paths["io"], CONTRACT_POLICY)
    observed_transitions = [
        {
            "category": difference["category"],
            "path": difference["path"],
            "before": difference["before"],
            "after": difference["after"],
        }
        for difference in data_to_io_contract["differences"]
    ]
    expected_transitions = campaign.get("required_transitions") or []
    transition_report = judge_transitions(expected_transitions, observed_transitions)

    io_event = _required_mapping(observation.get("io"), "events.io")
    loss_report = judge_loss_counts(
        io_event.get("expected_loss"),
        io_event.get("observed_loss"),
        io_event.get("reported_loss"),
    )
    fault_reports, fault_issues = _fault_report(
        campaign.get("fault_cases") or [], observation.get("faults") or []
    )

    fixture = _required_mapping(campaign.get("fixture"), "spec.fixture")
    expected_rows = fixture.get("rows")
    source_rows = observation.get("source_rows_observed_after_export")
    data_event = _required_mapping(observation.get("data"), "events.data")
    issues = list(fault_issues)
    checks = {
        "data_exit_code": type(data_event.get("exit_code")) is int
        and data_event.get("exit_code") == 0,
        "data_output_preexisting": data_event.get("output_preexisting") is False,
        "io_exit_code": type(io_event.get("exit_code")) is int
        and io_event.get("exit_code") == 0,
        "io_output_preexisting": io_event.get("output_preexisting") is False,
        "database_determinism": determinism["status"] == "pass",
        "database_to_data": database_to_data["status"] == "pass",
        "data_to_io_values": data_to_io_values["status"] == "pass",
        "data_to_io_transitions": transition_report["status"] == "pass",
        "data_to_io_loss": loss_report["status"] == "pass",
        "source_rows": source_rows == expected_rows,
        "data_rows": data_event.get("rows_in") == expected_rows
        and data_event.get("rows_out") == expected_rows,
        "io_rows": io_event.get("rows") == expected_rows,
    }
    issues.extend(name for name, passed in checks.items() if not passed)

    components = _required_mapping(campaign.get("components"), "spec.components")
    report = {
        "schema_version": 1,
        "campaign_id": campaign.get("campaign_id"),
        "executed_at": observation.get("executed_at"),
        "status": "fail" if issues else "pass",
        "scope": "live PostgreSQL read through Data identity transform and IO IPC rewrite",
        "component_revisions": {
            name: _required_mapping(value, f"spec.components.{name}").get("revision")
            for name, value in components.items()
        },
        "stage_execution": {
            "evidence_class": "attested_event",
            "data": {
                "exit_code": data_event.get("exit_code"),
                "output_preexisting": data_event.get("output_preexisting"),
            },
            "io": {
                "exit_code": io_event.get("exit_code"),
                "output_preexisting": io_event.get("output_preexisting"),
            },
        },
        "database_export": {
            "rows": expected_rows,
            "columns": determinism["before"]["columns"],
            "repetitions": 2,
            "determinism": "byte_exact" if determinism["status"] == "pass" else "fail",
            "sha256": determinism["before"]["artifact_sha256"],
            "source_rows_observed_after_export": source_rows,
            "row_order": "deterministic" if determinism["status"] == "pass" else "unverified",
        },
        "database_to_data": {
            "status": database_to_data["status"],
            "artifact_byte_identity": not database_to_data["differences"],
            "contract_identity": not any(
                row["category"] == "contract" for row in database_to_data["differences"]
            ),
            "value_identity": not any(
                row["category"] == "values" for row in database_to_data["differences"]
            ),
            "rows_before": database_to_data["before"]["rows"],
            "rows_after": database_to_data["after"]["rows"],
            "spill_bytes": data_event.get("spill_bytes"),
        },
        "data_to_io": {
            "status": (
                "pass_with_declared_transitions"
                if data_to_io_values["status"] == "pass"
                and transition_report["status"] == "pass"
                and loss_report["status"] == "pass"
                else "fail"
            ),
            "values": data_to_io_values["status"],
            "contract_identity": not data_to_io_contract["differences"],
            "transition_judge": transition_report["status"],
            "expected_transitions": len(expected_transitions),
            "observed_transitions": len(observed_transitions),
            "loss_judge": loss_report["status"],
            "expected_loss": loss_report["expected"],
            "observed_loss": loss_report["observed"],
            "reported_loss": loss_report["reported"],
            "output_sha256": data_to_io_values["after"]["artifact_sha256"],
        },
        "required_transitions": observed_transitions,
        "governed_rejections": fault_reports,
        "persistent_database_roundtrip": "not_demonstrated",
        "providers_not_exercised": ["mysql", "sqlserver"],
        "performance": {
            "status": "observational_only",
            "absolute_budget_approved": False,
        },
        "issues": issues,
    }
    return report


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
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = build_report(
        json.loads(arguments.spec.read_text(encoding="utf-8")),
        json.loads(arguments.events.read_text(encoding="utf-8")),
        arguments.artifacts,
    )
    _write_json_atomic(arguments.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
