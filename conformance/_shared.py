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

import json
from pathlib import Path

import pyarrow.ipc as ipc


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
    losses: list[str] = []
    for scope in ("schema", "field"):
        for key, value in before[scope].items():
            if key not in after[scope]:
                losses.append(f"{key}: perso (era {value!r})")
            elif after[scope][key] != value:
                losses.append(f"{key}: {value!r} -> {after[scope][key]!r}")
    return losses


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
    """`preserve_with_transition`: una transizione richiesta, e nient'altro.

    Un'etichetta che afferma ciò che il contenuto smentisce non va conservata:
    conservarla è rivendicare una risoluzione inesistente. La transizione è
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
