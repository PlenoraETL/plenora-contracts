"""Funzioni comuni ai runner della conformità.

Esiste perché lo stesso difetto è comparso due volte: `contract_from_stdout`
raccoglieva dal lato osservato solo le chiavi con prefisso `plenora.` mentre il
corpus le dichiara tutte, e la correzione applicata a `run_roundtrip.py` non
raggiungeva la copia in `run_chain.py`. Tredici casi della catena fallivano per
un difetto già corretto altrove.

È lo stesso argomento che l'ICD fa ai tre componenti in §15.3 — un modello
condiviso invece di tre divergenti — applicato qui. Due copie di una regola sono
due posti dove sbagliarla, e la seconda si scopre tardi.
"""

from __future__ import annotations

import ast
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pyarrow.ipc as ipc

if __package__:
    from .comparator import ComparisonError, compare_ipc
    from .fidelity import judge_allowed_transitions, judge_transitions
else:
    from comparator import ComparisonError, compare_ipc
    from fidelity import judge_allowed_transitions, judge_transitions


FIELD_METADATA_PATH = re.compile(r"^fields\[\d+\]\.metadata\[['\"](.+)['\"]\]$")


def observe(path: Path) -> dict[str, dict[str, str]]:
    """Metadati di schema e del campo geometry, decodificati."""
    table = ipc.open_file(str(path)).read_all()

    def decode(metadata) -> dict[str, str]:
        return {k.decode(): v.decode() for k, v in (metadata or {}).items()}

    field_metadata: dict[str, str] = {}
    if "geometry" in table.schema.names:
        field_metadata = decode(table.schema.field("geometry").metadata)
    return {"schema": decode(table.schema.metadata), "field": field_metadata}


def flatten(observed: dict[str, dict[str, str]]) -> dict[str, str]:
    return {**observed["schema"], **observed["field"]}


def diff(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> list[str]:
    changes: list[str] = []
    for scope in ("schema", "field"):
        for key in sorted(set(before[scope]) | set(after[scope])):
            before_value = before[scope].get(key)
            after_value = after[scope].get(key)
            if before_value != after_value:
                changes.append(f"{key}: {before_value!r} -> {after_value!r}")
    return changes


def contract_from_stdout(payload: str) -> dict[str, str]:
    """Chiavi canoniche dal JSON di un osservatore `arrow_to_contract`.

    I metadati del campo si raccolgono **tutti**, non solo quelli con prefisso
    `plenora.`: il corpus dichiara anche chiavi di standard esterni come
    `ARROW:extension:name`, e R2.4 impone di propagare ciò che non si
    interpreta. Filtrarle qui contraddiceva la regola che il runner verifica.
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
            observed[key] = str(value)
    return observed


def observe_scoped(path: Path) -> dict[str, str]:
    schema = ipc.open_file(str(path)).schema

    def decode(metadata: object) -> dict[str, str]:
        return {k.decode(): v.decode() for k, v in (metadata or {}).items()}

    observed = {
        f"schema.metadata[{key!r}]": value
        for key, value in decode(schema.metadata).items()
    }
    for index, field in enumerate(schema):
        observed.update(
            {
                f"fields[{index}].metadata[{key!r}]": value
                for key, value in decode(field.metadata).items()
            }
        )
    return observed


def contract_from_stdout_scoped(payload: str) -> dict[str, str]:
    document = json.loads(payload)
    observed = {
        f"schema.metadata[{key!r}]": str(value)
        for key, value in (document.get("schema_metadata") or {}).items()
    }
    if document.get("contract_version") is not None:
        observed["schema.metadata['plenora.contract.version']"] = str(
            document["contract_version"]
        )
    for index, entry in enumerate(document.get("fields", [])):
        metadata = {
            key: value for key, value in entry.items() if key.startswith("plenora.")
        }
        metadata.update(entry.get("metadata") or {})
        observed.update(
            {
                f"fields[{index}].metadata[{key!r}]": str(value)
                for key, value in metadata.items()
            }
        )
    return observed


def scoped_contract_divergences(
    declared: dict[str, str],
    observed: dict[str, str],
    declared_label: str,
    observed_label: str,
) -> list[str]:
    return [
        f"{key}: {declared_label} {declared.get(key, '<missing>')!r}, "
        f"{observed_label} {observed.get(key, '<missing>')!r}"
        for key in sorted(set(declared) | set(observed))
        if declared.get(key) != observed.get(key)
    ]


def expectation_for(expected: dict, role: str | None) -> str:
    """L'attesa dipende dal ruolo: R4.6 colloca il fail-closed.

    Un bordo di lettura dichiara e non rifiuta (R4.6.1); un bordo di scrittura
    rifiuta (R4.6.2); il centro decide e in assenza di decisione propaga
    (R4.6.3). Un'attesa unica chiederebbe a due dei tre il contrario del ruolo.
    """
    declared = expected.get("expect", "preserve")
    if declared != "by_role":
        return declared
    by_role = expected.get("expect_by_role") or {}
    return by_role.get(role, "preserve") if role else "preserve"


def requires_transition_judge(expected: dict, expectation: str) -> bool:
    return expectation == "preserve_with_transition" or bool(
        expected.get("allowed_transitions")
    )


SEMANTIC_IPC_POLICY = {
    "artifact_byte": False,
    "batch_structure": False,
    "contract": True,
    "values": True,
}


def _required_transition_rows(
    required: dict[str, object], observed: list[dict[str, object]]
) -> tuple[list[dict[str, object]], str | None]:
    rows: list[dict[str, object]] = []
    for key, raw_change in required.items():
        if not isinstance(raw_change, dict):
            return [], f"invalid required transition for {key!r}"
        suffix = f".metadata[{key!r}]"
        candidates = [
            str(row["path"])
            for row in observed
            if row.get("path") == key or str(row.get("path", "")).endswith(suffix)
        ]
        if len(candidates) > 1:
            return [], f"ambiguous required transition path for {key!r}: {candidates!r}"
        rows.append(
            {
                "category": "contract",
                "path": candidates[0] if candidates else key,
                "before": raw_change.get("from"),
                "after": raw_change.get("to"),
                "reason": "role_required_transition",
            }
        )
    return rows, None


def judge_ipc_transition(
    before: Path,
    after: Path,
    expected: dict,
    role: str | None,
) -> tuple[bool, str, list[dict[str, object]]]:
    """Judge every semantic value and contract difference source-to-output."""
    allowed = expected.get("allowed_transitions") or []
    required_by_role = expected.get("required_transitions") or {}
    if allowed and required_by_role:
        return (
            False,
            "fixture declares both allowed_transitions and required_transitions",
            [],
        )
    try:
        comparison = compare_ipc(before, after, SEMANTIC_IPC_POLICY)
    except (ComparisonError, OSError, ValueError, TypeError) as exc:
        return False, f"IPC comparison failed: {exc}", []

    differences = comparison["differences"]
    non_contract = [row for row in differences if row.get("category") != "contract"]
    if non_contract:
        categories = sorted({str(row.get("category")) for row in non_contract})
        return False, f"forbidden semantic differences: {categories!r}", differences

    observed = [dict(row) for row in differences]
    if allowed:
        report = judge_allowed_transitions(allowed, observed)
    else:
        required = required_by_role.get(role) or {}
        expected_rows, error = _required_transition_rows(required, observed)
        if error:
            return False, error, differences
        report = judge_transitions(expected_rows, observed)
    reason = "; ".join(
        issue if isinstance(issue, str) else json.dumps(issue, sort_keys=True)
        for issue in report["issues"]
    )
    return report["status"] == "pass", reason, differences


def write_json_atomic(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def judge_rejection(expected: dict, detail: str) -> tuple[bool, str]:
    """Un rifiuto vale solo se è il rifiuto giusto.

    Nella prima esecuzione della matrice un componente che respingeva ogni
    dataset per un backend CRS non abilitato superò il caso `fail_closed`: il
    runner accettava qualunque uscita diversa da zero.
    """
    signature = expected.get("expected_error") or {}
    hints = [h.lower() for h in signature.get("cause_hints", [])]
    disqualifying = [d.lower() for d in signature.get("disqualifying", [])]
    lowered = detail.lower()

    for marker in disqualifying:
        if marker in lowered:
            return False, (f"respinto per una ragione estranea al caso "
                           f"({marker!r} nel messaggio): non è evidenza che il "
                           f"conflitto sia rilevato")
    if hints and not any(hint in lowered for hint in hints):
        return False, ("respinto senza citare la causa attesa "
                       f"({', '.join(hints)}): rifiuto non attribuibile")
    return True, "respinto per la causa attesa"


def judge_transition(expected: dict, role: str | None,
                     losses: list[str]) -> tuple[bool, str, list[str]]:
    """Giudica transizioni opzionali o role-specific richieste, e nient'altro.

    `allowed_transitions` autorizza un subset opzionale; il formato legacy
    role-specific resta obbligatorio. In entrambi i casi ogni differenza non
    dichiarata resta una failure.
    """
    allowed = expected.get("allowed_transitions") or []
    expected_transitions = []
    for transition in allowed:
        normalized = dict(transition)
        match = FIELD_METADATA_PATH.fullmatch(str(normalized.get("path", "")))
        if match:
            normalized["path"] = match.group(1)
        expected_transitions.append(normalized)
    if not expected_transitions:
        required = (expected.get("required_transitions") or {}).get(role or "", {})
        expected_transitions = [
            {
                "category": "contract",
                "path": key,
                "before": change["from"],
                "after": change["to"],
                "reason": change.get("reason", "legacy_declared_transition"),
            }
            for key, change in sorted(required.items())
        ]
    observed_transitions = []
    try:
        for change in losses:
            key, values = change.split(": ", 1)
            before, after = values.split(" -> ", 1)
            observed_transitions.append(
                {
                    "category": "contract",
                    "path": key,
                    "before": ast.literal_eval(before),
                    "after": ast.literal_eval(after),
                }
            )
    except (SyntaxError, ValueError) as exc:
        problem = f"unparseable transition evidence: {exc}"
        return False, problem, [problem]

    judge = judge_allowed_transitions if allowed else judge_transitions
    verdict = judge(expected_transitions, observed_transitions)
    if verdict["status"] == "pass":
        detail = (
            "sole transizioni ammesse osservate, rappresentazioni invariate"
            if allowed
            else "transizione di stato richiesta osservata, rappresentazioni invariate"
        )
        return True, detail, []
    problems = [json.dumps(issue, sort_keys=True) for issue in verdict["issues"]]
    return False, "; ".join(problems), problems
