"""Compare published schema assertions against an immutable Git revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RATIFIED_BASE = "453c8d1ff2eb260840e6cedc033a2b76b58a0b9e"
ANNOTATIONS = {"$comment", "title", "description", "default", "examples", "deprecated", "readOnly", "writeOnly"}
SCHEMA_MAPS = {"$defs", "definitions", "properties", "patternProperties", "dependentSchemas"}
SCHEMA_ARRAYS = {"allOf", "anyOf", "oneOf", "prefixItems"}
SCHEMA_VALUES = {
    "additionalProperties", "unevaluatedProperties", "propertyNames", "contains",
    "additionalItems", "unevaluatedItems", "contentSchema", "not", "if", "then", "else",
}


def assertions(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key in ANNOTATIONS:
            continue
        if key in SCHEMA_MAPS:
            result[key] = {name: assertions(child) for name, child in value.items()}
        elif key in SCHEMA_ARRAYS or (key == "items" and isinstance(value, list)):
            result[key] = [assertions(child) for child in value]
        elif key in SCHEMA_VALUES or key == "items":
            result[key] = assertions(value)
        else:
            # Literal const/enum objects and unknown keywords are not schema nodes.
            result[key] = value
    return result


# Declared errata (COMPATIBILITY.md, «Errata before adoption»): an in-place
# change of a published schema accepted once, for the exact transition from
# the assertions digest `before` to `after`. Any other change of the same
# schema, or the same change of another schema, is still rejected.
ERRATA: dict[str, tuple[str, str, str]] = {
    "schemas/data-execution-result-v3.schema.json": (
        "679924dfaf4aa35c69ec7e859b86b4d6857a4dad80427e49c4243e4b64d7e9ab",
        "b5195ecca8f7be5062208ec9e42d77fa2aa8e9b551dd6c7e82cc38abbe42c8c6",
        "decisions/0008-data-run-runtime.md",
    ),
}


def assertions_digest(schema: Any) -> str:
    canonical = json.dumps(assertions(schema), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def declared_erratum(relative: str, previous: Any, current: Any) -> bool:
    erratum = ERRATA.get(relative)
    return erratum is not None and (
        assertions_digest(previous),
        assertions_digest(current),
    ) == erratum[:2]


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True, encoding="utf-8", stderr=subprocess.PIPE
    )


def check(root: Path, base: str) -> list[str]:
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("schema baseline must be a full immutable commit SHA")
    paths = git(root, "ls-tree", "-r", "--name-only", base, "--", "schemas").splitlines()
    paths = [path for path in paths if path.endswith(".schema.json")]
    if not paths:
        raise ValueError("schema baseline contains no versioned schemas")
    errors = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            errors.append(f"published schema removed: {relative}")
            continue
        previous = json.loads(git(root, "show", f"{base}:{relative}"))
        current = json.loads(path.read_text(encoding="utf-8"))
        if assertions(previous) != assertions(current) and not declared_erratum(
            relative, previous, current
        ):
            errors.append(f"published schema assertions changed: {relative}; introduce a new version")
    identifiers = set()
    for path in sorted((root / "schemas").glob("*.schema.json")):
        identifier = json.loads(path.read_text(encoding="utf-8")).get("$id")
        if not isinstance(identifier, str) or identifier in identifiers:
            errors.append(f"missing or duplicate schema identifier: {path.name}")
        if isinstance(identifier, str):
            identifiers.add(identifier)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("PLENORA_SCHEMA_BASE"))
    arguments = parser.parse_args()
    base = arguments.base
    if not base or base == "0" * 40:
        base = RATIFIED_BASE
    try:
        # The ratified floor remains protected even when a branch's prior push
        # already contained an invalid edit. The event base also protects newer schemas.
        errors = []
        for revision in dict.fromkeys([RATIFIED_BASE, base]):
            errors.extend(check(ROOT, revision))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"schema baseline check failed: {error}")
        return 1
    if errors:
        for error in errors:
            print(error)
        return 1
    print("published schema assertions unchanged; new schema identifiers are unique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
