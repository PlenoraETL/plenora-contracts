#!/usr/bin/env python3
"""Judge expected, observed, and component-reported fidelity loss exactly."""

from __future__ import annotations

import json
from typing import Any


def _normalize_counts(label: str, value: object) -> tuple[dict[str, int], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if not isinstance(value, dict):
        return {}, [
            {
                "kind": "invalid_loss_counts",
                "source": label,
                "detail": "loss counts must be an object",
            }
        ]

    normalized: dict[str, int] = {}
    for category, count in value.items():
        if not isinstance(category, str) or not category:
            issues.append(
                {
                    "kind": "invalid_loss_counts",
                    "source": label,
                    "detail": f"invalid category {category!r}",
                }
            )
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            issues.append(
                {
                    "kind": "invalid_loss_counts",
                    "source": label,
                    "category": category,
                    "detail": f"count must be a nonnegative integer, observed {count!r}",
                }
            )
            continue
        if count:
            normalized[category] = count

    return normalized, issues


def judge_loss_counts(
    expected: object,
    observed: object,
    reported: object,
) -> dict[str, Any]:
    expected_counts, expected_errors = _normalize_counts("expected", expected)
    observed_counts, observed_errors = _normalize_counts("observed", observed)
    reported_counts, reported_errors = _normalize_counts("reported", reported)
    validation_issues = [*expected_errors, *observed_errors, *reported_errors]
    if validation_issues:
        return {
            "status": "harness_error",
            "expected": expected_counts,
            "observed": observed_counts,
            "reported": reported_counts,
            "issues": validation_issues,
        }

    issues: list[dict[str, Any]] = []
    categories = sorted(
        set(expected_counts) | set(observed_counts) | set(reported_counts)
    )
    for category in categories:
        expected_count = expected_counts.get(category, 0)
        observed_count = observed_counts.get(category, 0)
        reported_count = reported_counts.get(category, 0)

        if observed_count > expected_count:
            issues.append(
                {
                    "kind": "forbidden_loss",
                    "category": category,
                    "count": observed_count - expected_count,
                    "expected": expected_count,
                    "observed": observed_count,
                }
            )
        elif observed_count < expected_count:
            issues.append(
                {
                    "kind": "expected_loss_missing",
                    "category": category,
                    "count": expected_count - observed_count,
                    "expected": expected_count,
                    "observed": observed_count,
                }
            )

        if observed_count > reported_count:
            issues.append(
                {
                    "kind": "unreported_loss",
                    "category": category,
                    "count": observed_count - reported_count,
                    "observed": observed_count,
                    "reported": reported_count,
                }
            )
        elif reported_count > observed_count:
            issues.append(
                {
                    "kind": "spurious_loss",
                    "category": category,
                    "count": reported_count - observed_count,
                    "observed": observed_count,
                    "reported": reported_count,
                }
            )

    return {
        "status": "fail" if issues else "pass",
        "expected": expected_counts,
        "observed": observed_counts,
        "reported": reported_counts,
        "issues": issues,
    }


def _normalize_transitions(
    label: str,
    value: object,
    *,
    require_reason: bool,
) -> tuple[dict[tuple[str, str, str, str], dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(value, list):
        return {}, [
            {
                "kind": "invalid_transitions",
                "source": label,
                "detail": "transitions must be an array",
            }
        ]

    required = {"category", "path", "before", "after"}
    allowed = required | ({"reason"} if require_reason else set())
    normalized: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, transition in enumerate(value):
        if not isinstance(transition, dict) or set(transition) != allowed:
            issues.append(
                {
                    "kind": "invalid_transitions",
                    "source": label,
                    "index": index,
                    "detail": f"transition keys must be exactly {sorted(allowed)}",
                }
            )
            continue
        category = transition["category"]
        path = transition["path"]
        reason = transition.get("reason")
        if (
            not isinstance(category, str)
            or not category
            or not isinstance(path, str)
            or not path
            or (require_reason and (not isinstance(reason, str) or not reason))
        ):
            issues.append(
                {
                    "kind": "invalid_transitions",
                    "source": label,
                    "index": index,
                    "detail": "category, path, and expected reason must be nonempty strings",
                }
            )
            continue
        try:
            before = json.dumps(transition["before"], sort_keys=True, separators=(",", ":"))
            after = json.dumps(transition["after"], sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            issues.append(
                {
                    "kind": "invalid_transitions",
                    "source": label,
                    "index": index,
                    "detail": f"before/after must be JSON values: {error}",
                }
            )
            continue
        key = (category, path, before, after)
        if key in normalized:
            issues.append(
                {
                    "kind": "invalid_transitions",
                    "source": label,
                    "index": index,
                    "detail": "duplicate transition",
                }
            )
            continue
        normalized[key] = transition
    return normalized, issues


def _judge_transition_set(
    expected: object,
    observed: object,
    *,
    require_all: bool,
) -> dict[str, Any]:
    expected_items, expected_errors = _normalize_transitions(
        "expected", expected, require_reason=True
    )
    observed_items, observed_errors = _normalize_transitions(
        "observed", observed, require_reason=False
    )
    validation_issues = [*expected_errors, *observed_errors]
    if validation_issues:
        return {
            "status": "harness_error",
            "expected": list(expected_items.values()),
            "observed": list(observed_items.values()),
            "issues": validation_issues,
        }

    issues: list[dict[str, Any]] = []
    for key in sorted(set(observed_items) - set(expected_items)):
        issues.append(
            {"kind": "forbidden_transition", "transition": observed_items[key]}
        )
    if require_all:
        for key in sorted(set(expected_items) - set(observed_items)):
            issues.append(
                {
                    "kind": "expected_transition_missing",
                    "transition": expected_items[key],
                }
            )
    return {
        "status": "fail" if issues else "pass",
        "expected": list(expected_items.values()),
        "observed": list(observed_items.values()),
        "issues": issues,
    }


def judge_transitions(expected: object, observed: object) -> dict[str, Any]:
    """Require observed transitions to match the required set exactly."""
    return _judge_transition_set(expected, observed, require_all=True)


def judge_allowed_transitions(allowed: object, observed: object) -> dict[str, Any]:
    """Allow any observed subset while rejecting undeclared transitions."""
    return _judge_transition_set(allowed, observed, require_all=False)
