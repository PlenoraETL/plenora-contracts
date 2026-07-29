#!/usr/bin/env python3
"""Esegue il corpus attraverso gli anelli disponibili e riporta cosa si perde.

Il runner non giudica «passa» o «non passa» soltanto: per ogni proprietà persa
indica **in quale anello** è sparita, confrontando i metadati osservati dopo
ogni stadio. Un caso rotto deve dire dove.

Gli stadi sono dichiarati in components.json, non qui: se una CLI cambia forma
la correzione è un dato, non una modifica di codice. Uno stadio con
`status != "available"` viene saltato e riportato come tale — mai come esito
positivo.

Solo la standard library e pyarrow.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow.ipc as ipc

# Piano data-tools neutro: filtra su una condizione sempre vera, così ogni
# perdita osservata dopo questo stadio è propagazione, non trasformazione.
IDENTITY_PLAN = {
    "schema_version": 4,
    "inputs": ["main"],
    "nodes": [
        {
            "id": "identity",
            "op": "table.filter",
            "in": ["main"],
            "config": {"column": "id", "operator": ">=", "value": 0},
        }
    ],
    "output": "identity",
}


def observe(path: Path) -> dict[str, dict[str, str]]:
    """Metadati di schema e del campo geometry, decodificati."""
    table = ipc.open_file(str(path)).read_all()

    def decode(metadata) -> dict[str, str]:
        return {k.decode(): v.decode() for k, v in (metadata or {}).items()}

    field_metadata: dict[str, str] = {}
    if "geometry" in table.schema.names:
        field_metadata = decode(table.schema.field("geometry").metadata)
    return {"schema": decode(table.schema.metadata), "field": field_metadata}


def diff(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> list[str]:
    losses: list[str] = []
    for scope in ("schema", "field"):
        for key, value in before[scope].items():
            if key not in after[scope]:
                losses.append(f"{key}: perso (era {value!r})")
            elif after[scope][key] != value:
                losses.append(f"{key}: {value!r} -> {after[scope][key]!r}")
    return losses


def expectation_for(expected: dict, role: str | None) -> str:
    """L'attesa dipende dal ruolo: R4.6 colloca il fail-closed. Vedi run_roundtrip.py."""
    declared = expected.get("expect", "preserve")
    if declared != "by_role":
        return declared
    by_role = expected.get("expect_by_role") or {}
    return by_role.get(role, "preserve") if role else "preserve"


def judge_rejection(expected: dict, detail: str) -> tuple[bool, str]:
    """Un rifiuto vale solo se e' il rifiuto giusto. Vedi run_roundtrip.py."""
    signature = expected.get("expected_error") or {}
    hints = [h.lower() for h in signature.get("cause_hints", [])]
    disqualifying = [d.lower() for d in signature.get("disqualifying", [])]
    lowered = detail.lower()
    for marker in disqualifying:
        if marker in lowered:
            return False, (f"respinto per una ragione estranea al caso "
                           f"({marker!r} nel messaggio)")
    if hints and not any(hint in lowered for hint in hints):
        return False, ("respinto senza citare la causa attesa "
                       f"({', '.join(hints)}): rifiuto non attribuibile")
    return True, "respinto per la causa attesa"


def run_stage(stage: dict, repo: Path, substitutions: dict[str, str]) -> tuple[bool, str]:
    command = [part.format(**substitutions) for part in stage["invocation"]]
    completed = subprocess.run(
        command, cwd=repo, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return False, detail[-800:]
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--cases", type=Path, default=root / "cases")
    parser.add_argument("--components", type=Path, default=root / "components.json")
    parser.add_argument("--checkouts", type=Path, default=root.parent.parent,
                        help="directory che contiene i tre checkout fratelli")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--only", action="append")
    arguments = parser.parse_args()

    manifest = json.loads(arguments.components.read_text(encoding="utf-8"))
    stages = manifest["stages"]

    for stage in stages:
        if stage["status"] != "available":
            print(f"stadio '{stage['id']}': {stage['status']} — {stage['blocker']}",
                  file=sys.stderr)

    runnable = [s for s in stages if s["status"] == "available"]
    if not runnable:
        print("nessuno stadio eseguibile", file=sys.stderr)
        return 2

    missing: list[str] = []
    for stage in runnable:
        repo = arguments.checkouts / stage["component"]
        if not (repo / "Cargo.toml").is_file():
            missing.append(str(repo))
    if missing:
        print("checkout assenti: " + ", ".join(missing), file=sys.stderr)
        return 2
    if shutil.which("cargo") is None:
        print("cargo non disponibile nel PATH", file=sys.stderr)
        return 2

    cases = sorted(p.stem for p in arguments.cases.glob("*.arrow"))
    if arguments.only:
        cases = [c for c in cases if c in arguments.only]
    if not cases:
        print(f"nessun caso in {arguments.cases}", file=sys.stderr)
        return 2

    results = []
    with tempfile.TemporaryDirectory(prefix="plenora-chain-") as directory:
        workspace = Path(directory)
        plan = workspace / "plan.json"
        plan.write_text(json.dumps(IDENTITY_PLAN, separators=(",", ":")), encoding="utf-8")

        for case in cases:
            expected = json.loads((arguments.cases / f"{case}.json").read_text(encoding="utf-8"))
            roles = {c["name"]: c.get("role") for c in manifest.get("components", [])}
            terminal_role = roles.get(runnable[-1]["component"])
            expectation = expectation_for(expected, terminal_role)
            fail_closed = expectation == "fail_closed"
            current = arguments.cases / f"{case}.arrow"
            observed = observe(current)
            record = {"case": case, "expect": expectation,
                      "terminal_role": terminal_role,
                      "rule": expected.get("rule"), "stages": []}

            for index, stage in enumerate(runnable):
                target = workspace / f"{case}.{stage['id']}.arrow"
                ok, detail = run_stage(
                    stage,
                    arguments.checkouts / stage["component"],
                    {"input": str(current), "output": str(target), "plan": str(plan)},
                )
                if not ok:
                    record["stages"].append(
                        {"stage": stage["id"], "outcome": "error", "detail": detail}
                    )
                    break
                after = observe(target)
                record["stages"].append(
                    {"stage": stage["id"], "outcome": "ok", "losses": diff(observed, after)}
                )
                observed, current = after, target

            errored = any(s["outcome"] == "error" for s in record["stages"])
            reached_end = len(record["stages"]) == len(runnable) and not errored
            losses = [loss for s in record["stages"] for loss in s.get("losses", [])]

            if fail_closed:
                # Un rifiuto vale solo se e' il rifiuto giusto: vedi
                # judge_rejection in run_roundtrip.py e la nota su
                # `expected_error` nel corpus.
                if not errored:
                    record["verdict"] = "fail"
                    record["reason"] = ("conflitto accettato in silenzio invece "
                                        "di fallire chiuso")
                else:
                    detail = record["stages"][-1].get("detail", "")
                    record["rejection"] = detail[-600:]
                    right, why = judge_rejection(expected, detail)
                    record["verdict"] = "pass" if right else "fail"
                    record["reason"] = why
            elif errored:
                record["verdict"] = "fail"
                record["reason"] = "errore in " + record["stages"][-1]["stage"]
            elif not reached_end:
                record["verdict"] = "incomplete"
            elif losses:
                record["verdict"] = "fail"
                record["reason"] = "; ".join(losses)
            else:
                record["verdict"] = "pass"
            results.append(record)

    for record in results:
        marker = {"pass": "  ok", "fail": "FAIL", "incomplete": "  ??"}[record["verdict"]]
        print(f"{marker}  {record['case']:<26} {record.get('reason', '')}")
        for entry in record["stages"]:
            for loss in entry.get("losses", []):
                print(f"          perso nello stadio '{entry['stage']}': {loss}")

    skipped = [s["id"] for s in stages if s["status"] != "available"]
    failed = [r["case"] for r in results if r["verdict"] != "pass"]
    print(f"\n{len(results) - len(failed)}/{len(results)} casi conformi"
          + (f", stadi non eseguiti: {', '.join(skipped)}" if skipped else ""))

    if arguments.report:
        arguments.report.write_text(
            json.dumps({"manifest_version": 1, "icd": manifest["icd"],
                        "stages_skipped": skipped, "cases": results},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Uno stadio saltato non è un successo: la catena non è verificata end-to-end.
    if skipped:
        return 1 if not failed else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
