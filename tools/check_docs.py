#!/usr/bin/env python3
"""Controlla che le guide correnti restino risolvibili e semanticamente sane.

Non valida lo stile della prosa. Protegge invece proprietà oggettive: link e
anchor locali, comandi Python esistenti in tools/ e sintassi degli esempi Python.
"""

from __future__ import annotations

import ast
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
# These published contractual trees are data, not editable documentation.
# Exclude them even when their prose contains stale links or commands.
IMMUTABLE_DIRECTORIES = {"schemas", "catalogs", "vectors", "bindings", "composition", "profiles"}
DOCUMENT_DIRECTORIES = ("decisions", "specs", "proposals", "conformance")
SKIP_PARTS = {".git", "__pycache__", "node_modules", ".venv"}
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
PYTHON_COMMAND = re.compile(
    r"\bpython(?:3)?\s+((?:(?:tools|scripts)[\\/])[A-Za-z0-9_.\\/-]+\.py)"
)
PYTHON_FENCE = re.compile(r"```python\s*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class Violation:
    path: Path
    reason: str


def markdown_documents(root: Path = ROOT) -> list[Path]:
    paths = list(root.glob("*.md"))
    for directory in DOCUMENT_DIRECTORIES:
        if directory in IMMUTABLE_DIRECTORIES:
            continue
        paths.extend((root / directory).rglob("*.md"))
    return sorted(path for path in paths if path.is_file()
                  and not SKIP_PARTS.intersection(path.relative_to(root).parts))


def github_slug(title: str) -> str:
    """Approssimazione deterministica degli anchor Markdown usati nel repo."""

    text = re.sub(r"<[^>]+>", "", title.strip().lower())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    found: set[str] = set()
    for heading in HEADING.findall(path.read_text(encoding="utf-8")):
        base = github_slug(heading)
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        found.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return found


def validate_links(root: Path, documents: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            target = raw.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, separator, anchor = target.partition("#")
            destination = path if not file_part else path.parent / unquote(file_part)
            if not destination.exists():
                violations.append(Violation(path, f"link locale inesistente: {raw}"))
                continue
            if separator and anchor and destination.suffix.lower() == ".md":
                if unquote(anchor).lower() not in anchors(destination):
                    violations.append(Violation(path, f"anchor inesistente: {raw}"))
    return violations


def validate_commands(root: Path, documents: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for command_path in PYTHON_COMMAND.findall(text):
            normalized = command_path.replace("\\", "/")
            if normalized.startswith("scripts/"):
                violations.append(Violation(path, f"comando Python deve usare tools/: {command_path}"))
            elif not (root / normalized).is_file():
                violations.append(
                    Violation(path, f"comando Python punta a un file assente: {command_path}")
                )
    return violations


def validate_python_examples(documents: list[Path]) -> list[Violation]:
    """Ogni esempio Python deve essere almeno sintatticamente eseguibile."""

    violations: list[Violation] = []
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for position, source in enumerate(PYTHON_FENCE.findall(text), start=1):
            try:
                compile(
                    source,
                    f"{path}#python-{position}",
                    "exec",
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
            except SyntaxError as exc:
                violations.append(
                    Violation(
                        path,
                        f"esempio Python {position} non valido: riga {exc.lineno}",
                    )
                )
    return violations


def scan(root: Path = ROOT) -> tuple[int, list[Violation]]:
    documents = markdown_documents(root)
    readable: list[Path] = []
    violations: list[Violation] = []
    for path in documents:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            violations.append(Violation(path, f"documento illeggibile: {exc}"))
            continue
        readable.append(path)
        if text.count("```") % 2:
            violations.append(Violation(path, "code fence non bilanciato"))
    violations += validate_links(root, readable)
    violations += validate_commands(root, readable)
    violations += validate_python_examples(readable)
    return len(documents), violations


def main() -> int:
    checked, violations = scan()
    if violations:
        for violation in violations:
            try:
                relative = violation.path.relative_to(ROOT)
            except ValueError:
                relative = violation.path
            print(f"{relative}: docs: {violation.reason}")
        return 1
    print(f"docs: {checked} documenti controllati, nessuna violazione")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
