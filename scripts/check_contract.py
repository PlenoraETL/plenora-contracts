#!/usr/bin/env python3
"""Controlli deterministici minimi sull'ICD Plenora.

Il programma usa soltanto la standard library. Non dimostra la conformità dei
componenti: impedisce regressioni strutturali nel documento che la definisce.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "PLENORA-CONTRATTI-TRASVERSALI.md"
README = ROOT / "README.md"
RATIFICATION_CANDIDATE = ROOT / "docs" / "RATIFICATION-CANDIDATE-2.0.md"

VERSION_RE = re.compile(
    r"^\*\*Documento normativo di interfaccia \(ICD\) · versione "
    r"(?P<version>[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[0-9A-Za-z.-]+)?) · ",
    re.MULTILINE,
)
REQUIREMENT_DEFINITION_RE = re.compile(
    r"^>\s+\*\*(?P<id>R[0-9]+(?:\.[0-9]+)+)\b", re.MULTILINE
)
ALLOWED_REGISTRY_STATES = ("ratificata", "proposta", "sospesa", "superata")
REQUIRED_APPENDICES = (
    "## Appendice A — Riepilogo di conformità",
    "## Appendice B — Hazard di riferimento",
    "## Appendice C — Tabelle di rinomina",
    "## Appendice D — Glossario",
    "## Appendice E — Matrice minima di verifica",
)
FORBIDDEN_STALE_TEXT = (
    "`futures-core` per `cancelled()`",
    "è sospesa in attesa della versione 2.0",
    "modifica entra in vigore quando i tre team l'hanno recepita",
    "Documento redatto come revisione tecnica indipendente",
    "`driver.rs:347`",
    "95 `unwrap_or*`",
    "IO-tools | 7, `snake_case`",
    "IO-tools | `PlenoraError`",
)


def read_utf8(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: lettura UTF-8 fallita: {exc}")
        return ""


def unescaped_pipe_count(line: str) -> int:
    return len(re.findall(r"(?<!\\)\|", line))


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line)[1:-1]]


def registry_rows(document: str, errors: list[str]) -> list[str]:
    lines = document.splitlines()
    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if line.startswith("> | Sezione | Oggetto | Stato |")
        )
    except StopIteration:
        errors.append("registro di ratifica: intestazione tabella assente")
        return []

    rows: list[str] = []
    for line in lines[start:]:
        if line.startswith("> |"):
            rows.append(line)
            continue
        break

    if len(rows) < 3:
        errors.append("registro di ratifica: tabella vuota o interrotta")
        return rows

    expected_pipes = unescaped_pipe_count(rows[0])
    for offset, row in enumerate(rows, start=start + 1):
        actual_pipes = unescaped_pipe_count(row)
        if actual_pipes != expected_pipes:
            errors.append(
                "registro di ratifica:"
                f" riga {offset} ha {actual_pipes} separatori, attesi {expected_pipes}"
            )

    for offset, row in enumerate(rows[2:], start=start + 3):
        cells = table_cells(row)
        state_cell = cells[2] if len(cells) >= 3 else ""
        states = [
            state
            for state in ALLOWED_REGISTRY_STATES
            if re.search(rf"\b{re.escape(state)}\b", state_cell)
        ]
        if len(states) != 1:
            errors.append(
                f"registro di ratifica: riga {offset} non ha un solo stato ammesso"
            )

    return rows[2:]


def validate_document(
    document: str, readme: str, ratification_candidate: str
) -> dict[str, object]:
    errors: list[str] = []

    if "\ufffd" in document or "\x00" in document:
        errors.append("documento: carattere di sostituzione Unicode o NUL presente")

    for line_number, line in enumerate(document.splitlines(), start=1):
        if line.endswith((" ", "\t")):
            errors.append(f"documento: whitespace finale alla riga {line_number}")

    version_match = VERSION_RE.search(document)
    version = version_match.group("version") if version_match else None
    if version is None:
        errors.append("documento: versione ICD assente o non valida")
    elif version not in readme:
        errors.append(f"README: versione ICD {version} non citata")

    definitions = REQUIREMENT_DEFINITION_RE.findall(document)
    duplicates = sorted(
        requirement
        for requirement in set(definitions)
        if definitions.count(requirement) > 1
    )
    if duplicates:
        errors.append(
            "documento: identificativi normativi duplicati: " + ", ".join(duplicates)
        )

    for requirement in ("R0.1", "R0.2", "R0.3", "R0.4", "R0.5"):
        if requirement not in definitions:
            errors.append(f"documento: requisito assurance {requirement} assente")

    rows = registry_rows(document, errors)
    ratified_rows = sum(
        bool(re.search(r"\bratificata\b", table_cells(row)[2])) for row in rows
    )
    if ratified_rows != 11:
        errors.append(
            "registro di ratifica:"
            f" {ratified_rows} righe ratificate, ma la baseline ne dichiara 11"
        )

    for heading in REQUIRED_APPENDICES:
        if document.count(heading) != 1:
            errors.append(f"documento: appendice assente o duplicata: {heading}")

    for stale_text in FORBIDDEN_STALE_TEXT:
        if stale_text in document or stale_text in readme:
            errors.append(f"testo obsoleto presente: {stale_text!r}")

    required_candidate_clauses = (
        "Stato: **non ratificato**.",
        "| IO-tools | da registrare |",
        "| data-tools | da registrare |",
        "| database-tools | da registrare |",
        "Revisore diverso dall'autore",
    )
    for clause in required_candidate_clauses:
        if clause not in ratification_candidate:
            errors.append(
                "candidato di ratifica: clausola di governance assente:"
                f" {clause!r}"
            )

    required_clauses = (
        "valori unici, ordinati come in §3.1, senza spazi",
        "`northing_easting` \\| `other` \\| `unknown`",
        "Il future restituito da `cancelled()`",
        "§11.5–§11.10",
        "capability non atomica",
        "tag firmato della baseline",
    )
    for clause in required_clauses:
        if clause not in document:
            errors.append(f"documento: clausola di coerenza assente: {clause!r}")

    return {
        "document": str(DOCUMENT.relative_to(ROOT)),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "revision": os.environ.get("GITHUB_SHA", "working-tree"),
        "version": version,
        "requirement_definitions": len(definitions),
        "registry_rows": len(rows),
        "ratified_rows": ratified_rows,
        "errors": errors,
        "status": "pass" if not errors else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        help="scrive anche il report machine-readable nel percorso indicato",
    )
    args = parser.parse_args()

    read_errors: list[str] = []
    document = read_utf8(DOCUMENT, read_errors)
    readme = read_utf8(README, read_errors)
    ratification_candidate = read_utf8(RATIFICATION_CANDIDATE, read_errors)
    report = validate_document(document, readme, ratification_candidate)
    report["errors"] = [*read_errors, *report["errors"]]
    report["status"] = "pass" if not report["errors"] else "fail"

    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(encoded)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(encoded + "\n", encoding="utf-8")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
