#!/usr/bin/env python3
"""Exercise every rewrite-stage order and compare their final Arrow artifacts."""

from __future__ import annotations

import argparse
import itertools
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import (  # noqa: E402
    contract_from_stdout,
    expectation_for,
    flatten,
    judge_ipc_transition,
    judge_rejection,
    observe,
    write_json_atomic,
)
from comparator import compare_ipc  # noqa: E402
from run_chain import IDENTITY_PLAN  # noqa: E402


SEMANTIC_POLICY = {
    "artifact_byte": False,
    "batch_structure": False,
    "contract": True,
    "values": True,
}


def invoke(stage: dict, repo: Path, substitutions: dict[str, str]) -> subprocess.CompletedProcess[str]:
    command = [part.format(**substitutions) for part in stage["invocation"]]
    return subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def judge_terminal(
    judge: dict | None,
    roles: dict[str, str | None],
    expected: dict,
    artifact: Path,
    checkouts: Path,
) -> dict[str, object]:
    if judge is None:
        return {"status": "fail", "reason": "terminal observer unavailable"}
    completed = invoke(
        judge,
        checkouts / judge["component"],
        {"input": str(artifact), "output": "", "plan": ""},
    )
    expectation = expectation_for(expected, roles.get(judge["component"]))
    detail = (completed.stderr or completed.stdout or "").strip()
    if completed.returncode != 0:
        if expectation == "fail_closed":
            accepted, reason = judge_rejection(expected, detail)
            return {
                "status": "pass" if accepted else "fail",
                "outcome": "rejected",
                "reason": reason,
            }
        return {"status": "fail", "outcome": "rejected", "reason": detail[-500:]}
    if expectation == "fail_closed":
        return {
            "status": "fail",
            "outcome": "accepted",
            "reason": "terminal observer accepted a fail-closed case",
        }
    try:
        seen = contract_from_stdout(completed.stdout)
    except (json.JSONDecodeError, AttributeError) as exc:
        return {"status": "fail", "outcome": "unreadable", "reason": str(exc)}
    declared = flatten(observe(artifact))
    divergences = [
        f"{key}: artifact {value!r}, observer {seen.get(key, '<missing>')!r}"
        for key, value in declared.items()
        if seen.get(key) != value
    ]
    return {
        "status": "fail" if divergences else "pass",
        "outcome": "accepted",
        "divergences": divergences,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--cases", type=Path, default=root / "cases")
    parser.add_argument("--components", type=Path, default=root / "components.json")
    parser.add_argument("--checkouts", type=Path, default=root.parent.parent)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--only", action="append")
    arguments = parser.parse_args(argv)

    manifest = json.loads(arguments.components.read_text(encoding="utf-8"))
    roles = {row["name"]: row.get("role") for row in manifest.get("components", [])}
    rewrite_stages = [row for row in manifest["stages"] if row.get("invocation")]
    stages = [row for row in rewrite_stages if row["status"] == "available"]
    skipped = [row["id"] for row in rewrite_stages if row["status"] != "available"]
    if skipped or len(stages) < 2:
        print(f"pairwise requires every rewrite stage; skipped={skipped!r}", file=sys.stderr)
        return 2
    if shutil.which("cargo") is None:
        print("cargo non disponibile nel PATH", file=sys.stderr)
        return 2
    missing = [
        str(arguments.checkouts / stage["component"])
        for stage in stages
        if not (arguments.checkouts / stage["component"] / "Cargo.toml").is_file()
    ]
    if missing:
        print(f"checkout assenti: {missing!r}", file=sys.stderr)
        return 2

    judge = next(
        (
            row
            for row in manifest.get("roundtrips", [])
            if row.get("kind") == "arrow_to_contract"
            and row.get("status") == "available"
        ),
        None,
    )
    cases = sorted(path.stem for path in arguments.cases.glob("*.arrow"))
    if arguments.only:
        cases = [case for case in cases if case in arguments.only]
    if not cases:
        print("nessun caso pairwise", file=sys.stderr)
        return 2

    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="plenora-pairwise-") as directory:
        workspace = Path(directory)
        plan = workspace / "plan.json"
        plan.write_text(
            json.dumps(IDENTITY_PLAN, separators=(",", ":")), encoding="utf-8"
        )
        for case in cases:
            source = arguments.cases / f"{case}.arrow"
            expected = json.loads(
                (arguments.cases / f"{case}.json").read_text(encoding="utf-8")
            )
            record: dict[str, object] = {
                "case": case,
                "orders": [],
                "comparisons": [],
            }
            outputs: dict[str, Path] = {}
            for order in itertools.permutations(stages):
                order_id = "->".join(stage["id"] for stage in order)
                current = source
                order_record: dict[str, object] = {
                    "order": [stage["id"] for stage in order],
                    "stages": [],
                }
                rejected = False
                for index, stage in enumerate(order):
                    target = workspace / f"{case}.{order_id}.{index}.arrow"
                    completed = invoke(
                        stage,
                        arguments.checkouts / stage["component"],
                        {
                            "input": str(current),
                            "output": str(target),
                            "plan": str(plan),
                        },
                    )
                    expectation = expectation_for(expected, roles.get(stage["component"]))
                    detail = (completed.stderr or completed.stdout or "").strip()
                    if completed.returncode != 0:
                        accepted, reason = (
                            judge_rejection(expected, detail)
                            if expectation == "fail_closed"
                            else (False, detail[-500:])
                        )
                        order_record["stages"].append(
                            {
                                "stage": stage["id"],
                                "outcome": "rejected",
                                "accepted": accepted,
                                "reason": reason,
                            }
                        )
                        order_record["verdict"] = "pass" if accepted else "fail"
                        rejected = True
                        break
                    if expectation == "fail_closed":
                        order_record["stages"].append(
                            {
                                "stage": stage["id"],
                                "outcome": "accepted",
                                "accepted": False,
                            }
                        )
                        order_record["verdict"] = "fail"
                        rejected = True
                        break
                    passed, reason, differences = judge_ipc_transition(
                        current,
                        target,
                        expected,
                        roles.get(stage["component"]),
                    )
                    order_record["stages"].append(
                        {
                            "stage": stage["id"],
                            "outcome": "accepted",
                            "semantic_status": "pass" if passed else "fail",
                            "reason": reason or "semantic contract preserved",
                            "differences": differences,
                        }
                    )
                    if not passed:
                        order_record["verdict"] = "fail"
                        rejected = True
                        break
                    current = target

                if not rejected:
                    terminal = judge_terminal(
                        judge, roles, expected, current, arguments.checkouts
                    )
                    passed = terminal["status"] == "pass"
                    order_record.update(
                        {
                            "terminal_observer": terminal,
                            "verdict": "pass" if passed else "fail",
                        }
                    )
                    outputs[order_id] = current
                record["orders"].append(order_record)

            for left, right in itertools.combinations(sorted(outputs), 2):
                comparison = compare_ipc(outputs[left], outputs[right], SEMANTIC_POLICY)
                record["comparisons"].append(
                    {
                        "left": left,
                        "right": right,
                        "status": comparison["status"],
                        "differences": comparison["differences"],
                    }
                )
            order_records = record["orders"]
            assert isinstance(order_records, list)
            comparisons = record["comparisons"]
            assert isinstance(comparisons, list)
            passed = all(row.get("verdict") == "pass" for row in order_records)
            if outputs:
                passed = passed and len(outputs) == len(order_records)
                passed = passed and all(row["status"] == "pass" for row in comparisons)
            record["verdict"] = "pass" if passed else "fail"
            results.append(record)

    report = {
        "manifest_version": 1,
        "icd": manifest["icd"],
        "component_revisions": {
            row["name"]: row["revision"] for row in manifest["components"]
        },
        "orders": [list(order) for order in itertools.permutations([row["id"] for row in stages])],
        "cases": results,
    }
    write_json_atomic(arguments.report, report)
    failed = [row["case"] for row in results if row["verdict"] != "pass"]
    print(f"{len(results) - len(failed)}/{len(results)} pairwise conformi")
    for case in failed:
        print(f"  FAIL {case}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
