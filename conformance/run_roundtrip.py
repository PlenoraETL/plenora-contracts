#!/usr/bin/env python3
"""Verifica ogni componente da solo: legge il corpus, lo riscrive, si confronta.

Se un componente conserva il contratto in entrata e in uscita, ogni
composizione lo conserva. Questo test isola il colpevole senza catena da
bisezionare, senza gli altri due installati e senza ordine di esecuzione: è il
motivo per cui viene prima di run_chain.py.

Due generi di roundtrip, dichiarati in components.json:

  arrow_to_arrow      il componente riscrive un file Arrow: si confrontano i
                      metadati prima e dopo;
  arrow_to_contract   il componente osserva il dataset e stampa il contratto in
                      JSON: si confronta il contratto osservato con quello
                      dichiarato dal corpus.

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
# differenza osservata è propagazione mancata e non trasformazione.
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


def flatten(observed: dict[str, dict[str, str]]) -> dict[str, str]:
    return {**observed["schema"], **observed["field"]}


def contract_from_stdout(payload: str) -> dict[str, str]:
    """Estrae le chiavi canoniche dal JSON di un roundtrip arrow_to_contract.

    Accetta sia una mappa piatta di metadati sia la forma dichiarata in
    components.json, dove i campi stanno sotto `fields`.
    """
    document = json.loads(payload)
    observed: dict[str, str] = {}
    for key, value in document.items():
        if key.startswith("plenora."):
            observed[key] = str(value)
    for key, value in (document.get("schema_metadata") or {}).items():
        if key.startswith("plenora."):
            observed[key] = str(value)
    if document.get("contract_version") is not None:
        observed["plenora.contract.version"] = str(document["contract_version"])
    for entry in document.get("fields", []):
        for key, value in entry.items():
            if key.startswith("plenora."):
                observed[key] = str(value)
        for key, value in (entry.get("metadata") or {}).items():
            if key.startswith("plenora."):
                observed[key] = str(value)
    return observed


def expectation_for(expected: dict, role: str | None) -> str:
    """L'attesa dipende dal ruolo del componente: R4.6 colloca il fail-closed.

    Un bordo di lettura dichiara l'incoerenza e non rifiuta (R4.6.1); un bordo
    di scrittura rifiuta (R4.6.2); il centro decide e in assenza di decisione
    propaga (R4.6.3). Un'attesa unica chiederebbe a due dei tre il contrario
    del proprio ruolo.
    """
    declared = expected.get("expect", "preserve")
    if declared != "by_role":
        return declared
    by_role = expected.get("expect_by_role") or {}
    if role is None or role not in by_role:
        return "preserve"
    return by_role[role]


def judge_transition(expected: dict, role: str | None,
                     losses: list[str]) -> tuple[bool, str, list[str]]:
    """`preserve_with_transition`: una transizione richiesta, e nient'altro.

    Un'etichetta che afferma cio' che il contenuto smentisce non va conservata:
    conservarla e' rivendicare una risoluzione inesistente. La transizione e'
    quindi obbligatoria — se manca il caso fallisce — e ogni altra differenza
    resta una perdita.
    """
    required = (expected.get("required_transitions") or {}).get(role or "", {})
    problems: list[str] = []
    remaining = list(losses)

    for key, change in required.items():
        atteso = f"{key}: {change['from']!r} -> {change['to']!r}"
        if atteso in remaining:
            remaining.remove(atteso)
        else:
            problems.append(f"transizione richiesta assente: {atteso}. "
                            "Conservare lo stato in ingresso significa "
                            "rivendicare una risoluzione che il contenuto smentisce")
    problems.extend(remaining)
    if problems:
        return False, "; ".join(problems), problems
    return True, ("transizione di stato richiesta osservata, "
                  "rappresentazioni invariate"), []


def judge_rejection(expected: dict, detail: str) -> tuple[bool, str]:
    """Un rifiuto vale solo se e' il rifiuto giusto.

    Nella prima esecuzione della matrice un componente che respingeva ogni
    dataset per un backend CRS non abilitato ha superato il caso `fail_closed`:
    il runner accettava qualunque uscita diversa da zero. Ora la fixture
    dichiara le tracce della causa attesa e quelle che la squalificano.
    """
    signature = expected.get("expected_error") or {}
    hints = [h.lower() for h in signature.get("cause_hints", [])]
    disqualifying = [d.lower() for d in signature.get("disqualifying", [])]
    lowered = detail.lower()

    for marker in disqualifying:
        if marker in lowered:
            return False, (f"respinto per una ragione estranea al caso "
                           f"({marker!r} nel messaggio): non e' evidenza che il "
                           f"conflitto sia rilevato")
    if hints and not any(hint in lowered for hint in hints):
        return False, ("respinto senza citare la causa attesa "
                       f"({', '.join(hints)}): rifiuto non attribuibile")
    return True, "respinto per la causa attesa"


def run(invocation: list[str], repo: Path, substitutions: dict[str, str]):
    command = [part.format(**substitutions) for part in invocation]
    return subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--cases", type=Path, default=root / "cases")
    parser.add_argument("--components", type=Path, default=root / "components.json")
    parser.add_argument("--checkouts", type=Path, default=root.parent.parent,
                        help="directory che contiene i tre checkout fratelli")
    parser.add_argument("--component", action="append",
                        help="limita a uno o più roundtrip per id")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()

    manifest = json.loads(arguments.components.read_text(encoding="utf-8"))
    roles = {c["name"]: c.get("role") for c in manifest.get("components", [])}
    roundtrips = manifest["roundtrips"]
    if arguments.component:
        roundtrips = [r for r in roundtrips if r["id"] in arguments.component]

    for entry in roundtrips:
        if entry["status"] != "available":
            print(f"roundtrip '{entry['id']}': {entry['status']} — non eseguito",
                  file=sys.stderr)

    runnable = [r for r in roundtrips if r["status"] == "available"]
    if not runnable:
        print("nessun roundtrip eseguibile", file=sys.stderr)
        return 2
    if shutil.which("cargo") is None:
        print("cargo non disponibile nel PATH", file=sys.stderr)
        return 2

    absent = [str(arguments.checkouts / r["component"]) for r in runnable
              if not (arguments.checkouts / r["component"] / "Cargo.toml").is_file()]
    if absent:
        print("checkout assenti: " + ", ".join(absent), file=sys.stderr)
        return 2

    cases = sorted(p.stem for p in arguments.cases.glob("*.arrow"))
    if not cases:
        print(f"nessun caso in {arguments.cases}", file=sys.stderr)
        return 2

    results = []
    with tempfile.TemporaryDirectory(prefix="plenora-roundtrip-") as directory:
        workspace = Path(directory)
        plan = workspace / "plan.json"
        plan.write_text(json.dumps(IDENTITY_PLAN, separators=(",", ":")), encoding="utf-8")

        for entry in runnable:
            repo = arguments.checkouts / entry["component"]
            for case in cases:
                source = arguments.cases / f"{case}.arrow"
                expected = json.loads(
                    (arguments.cases / f"{case}.json").read_text(encoding="utf-8")
                )
                role = roles.get(entry["component"])
                expectation = expectation_for(expected, role)
                fail_closed = expectation == "fail_closed"
                target = workspace / f"{entry['id']}.{case}.arrow"
                completed = run(entry["invocation"], repo,
                                {"input": str(source), "output": str(target),
                                 "plan": str(plan)})
                record = {"roundtrip": entry["id"], "component": entry["component"],
                          "case": case, "kind": entry["kind"],
                          "expect": expectation,
                          "role": role}

                if completed.returncode != 0:
                    detail = (completed.stderr or completed.stdout or "").strip()
                    # L'evidenza del rifiuto va conservata proprio dove conta.
                    record["rejection"] = detail[-600:]
                    if fail_closed:
                        right, why = judge_rejection(expected, detail)
                        record["verdict"] = "pass" if right else "fail"
                        record["reason"] = why
                    else:
                        record["verdict"] = "fail"
                        record["reason"] = f"errore: {detail[-400:]}"
                    results.append(record)
                    continue

                if fail_closed:
                    record["verdict"] = "fail"
                    record["reason"] = ("conflitto accettato in silenzio invece "
                                        "di fallire chiuso")
                    results.append(record)
                    continue

                if entry["kind"] == "arrow_to_arrow":
                    if not target.is_file():
                        record["verdict"] = "fail"
                        record["reason"] = "nessun file prodotto"
                    elif expectation == "preserve_with_transition":
                        losses = diff(observe(source), observe(target))
                        ok, why, residual = judge_transition(expected, role, losses)
                        record["verdict"] = "pass" if ok else "fail"
                        record["reason"] = why
                        record["losses"] = residual
                        record["observed_changes"] = losses
                    else:
                        losses = diff(observe(source), observe(target))
                        record["verdict"] = "fail" if losses else "pass"
                        record["losses"] = losses
                        if expected.get("expect") == "by_role"                                 and expectation == "preserve":
                            record["unverified_obligation"] = (
                                "R4.6.1 impone di preservare *e* di dichiarare "
                                "l'incoerenza nel LossReport o FidelityAssessment. "
                                "Questo runner verifica solo la preservazione: un "
                                "esito positivo non e' evidenza che l'incoerenza sia "
                                "stata dichiarata.")
                else:
                    declared = flatten(observe(source))
                    try:
                        seen = contract_from_stdout(completed.stdout)
                    except (json.JSONDecodeError, AttributeError):
                        record["verdict"] = "fail"
                        record["reason"] = "stdout non è JSON conforme a expected_output"
                        results.append(record)
                        continue
                    losses = [f"{key}: dichiarato {value!r}, osservato "
                              f"{seen.get(key, '<assente>')!r}"
                              for key, value in declared.items()
                              if seen.get(key) != value]
                    record["verdict"] = "fail" if losses else "pass"
                    record["losses"] = losses
                results.append(record)

    for entry in runnable:
        rows = [r for r in results if r["roundtrip"] == entry["id"]]
        good = sum(1 for r in rows if r["verdict"] == "pass")
        print(f"\n{entry['component']}  ({entry['kind']})  {good}/{len(rows)} conformi")
        for record in rows:
            if record["verdict"] == "pass":
                continue
            print(f"  FAIL  {record['case']:<26} {record.get('reason', '')}")
            for loss in record.get("losses", []):
                print(f"           {loss}")

    skipped = [r["id"] for r in roundtrips if r["status"] != "available"]
    failed = [r for r in results if r["verdict"] != "pass"]
    print(f"\n{len(results) - len(failed)}/{len(results)} verifiche conformi"
          + (f", roundtrip non eseguiti: {', '.join(skipped)}" if skipped else ""))

    if arguments.report:
        arguments.report.write_text(
            json.dumps({"manifest_version": 1, "icd": manifest["icd"],
                        "roundtrips_skipped": skipped, "verifications": results},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Un roundtrip non eseguito non è un successo: la copertura non è completa.
    return 1 if failed or skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
