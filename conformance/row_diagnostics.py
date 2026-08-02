from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).with_name("schemas") / "row-diagnostics-v1.schema.json"


def validate_report(report: Mapping[str, Any]) -> None:
    """Validate one row-scoped diagnostic report.

    Raises ``ValueError`` when either the JSON shape or a cross-field arithmetic
    invariant is invalid.
    """

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(report),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ValueError(f"schema violation at {location}: {error.message}")

    observed_total = report["observed_total"]
    counts_sum = sum(report["counts"].values())
    if counts_sum != observed_total:
        raise ValueError(
            f"counts sum {counts_sum} does not match observed_total {observed_total}"
        )

    if "total" in report and report["total"] < observed_total:
        raise ValueError("report total is less than observed_total")
    if report["completeness"] == "complete" and report["total"] != observed_total:
        raise ValueError("complete report total does not match observed_total")
    if report["scope"] == "write" and observed_total > report["input_total"]:
        raise ValueError("observed_total exceeds input_total for write report")

    examples_length = len(report["examples"])
    if examples_length > report["examples_limit"]:
        raise ValueError("examples exceed examples_limit")
    if examples_length > observed_total:
        raise ValueError("examples exceed observed_total")
    required_examples = min(observed_total, report["examples_limit"])
    if report["completeness"] == "complete" and examples_length != required_examples:
        raise ValueError(
            f"complete report must provide {required_examples} examples, "
            f"got {examples_length}"
        )
    expected_truncated = (
        observed_total > examples_length
        and examples_length == report["examples_limit"]
    )
    if report["examples_truncated"] != expected_truncated:
        raise ValueError(
            "examples_truncated is true only when examples_limit omits observed rows"
        )
    source_indices: set[int] = set()
    example_cause_counts = {cause: 0 for cause in report["counts"]}
    for example in report["examples"]:
        source_index = example["source_index"]
        if source_index in source_indices:
            raise ValueError(f"duplicate source_index in examples: {source_index}")
        source_indices.add(source_index)
        if example["cause"] not in report["counts"]:
            raise ValueError(f"example cause absent from counts: {example['cause']}")
        example_cause_counts[example["cause"]] += 1
    for cause, example_count in example_cause_counts.items():
        if example_count > report["counts"][cause]:
            raise ValueError(f"examples exceed count for cause: {cause}")

    if report["scope"] == "write":
        partition = report["write_outcome"]
        diagnostic_states = report["diagnostic_state_counts"]
        diagnostic_state_sum = sum(diagnostic_states.values())
        if diagnostic_state_sum != observed_total:
            raise ValueError(
                f"diagnostic state sum {diagnostic_state_sum} does not match "
                f"observed_total {observed_total}"
            )
        example_state_counts = {state: 0 for state in diagnostic_states}
        for example in report["examples"]:
            example_state_counts[example["write_state"]] += 1
        for state, diagnostic_count in diagnostic_states.items():
            bucket = partition[state]
            if bucket["state"] == "known" and diagnostic_count > bucket["value"]:
                raise ValueError(
                    f"diagnostic {state} count exceeds known write outcome bucket"
                )
            if example_state_counts[state] > diagnostic_count:
                raise ValueError(
                    f"example {state} count exceeds diagnostic state count"
                )
        known_sum = sum(
            bucket["value"]
            for bucket in partition.values()
            if bucket["state"] == "known"
        )
        if known_sum > report["input_total"]:
            raise ValueError(
                f"known write outcome sum {known_sum} exceeds "
                f"input_total {report['input_total']}"
            )
        diagnosed_unknown = sum(
            diagnostic_states[state]
            for state, bucket in partition.items()
            if bucket["state"] == "unknown"
        )
        if known_sum + diagnosed_unknown > report["input_total"]:
            raise ValueError(
                "known outcomes plus diagnosed unknown rows exceed input_total"
            )
        if all(bucket["state"] == "known" for bucket in partition.values()):
            if known_sum != report["input_total"]:
                raise ValueError(
                    f"write outcome sum {known_sum} does not match "
                    f"input_total {report['input_total']}"
                )
