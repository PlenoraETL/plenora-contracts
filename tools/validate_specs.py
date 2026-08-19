from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

CASES = {
    "valid": {
        "cli-envelope-v2.schema.json": [
            "examples/valid/cli-success.json",
            "examples/valid/cli-error.json",
        ],
        "capabilities-v1.schema.json": ["examples/valid/capabilities.json"],
        "capabilities-v2.schema.json": ["examples/valid/capabilities-v2.json"],
        "row-diagnostics-v1.schema.json": [
            "examples/valid/row-diagnostics.json"
        ],
        "adoption-manifest-v1.schema.json": [
            "examples/valid/adoption-manifest.json"
        ],
        "adoption-manifest-v2.schema.json": [
            "examples/valid/adoption-manifest-v2.json"
        ],
    },
    "invalid": {
        "cli-envelope-v2.schema.json": [
            "examples/invalid/cli-missing-protocol.json"
        ],
        "error-v1.schema.json": [
            "examples/invalid/error-after-missing-delay.json"
        ],
        "capabilities-v1.schema.json": [
            "examples/invalid/capabilities-unavailable-without-reason.json"
        ],
        "capabilities-v2.schema.json": [
            "examples/invalid/capabilities-v2-unavailable-without-reason.json"
        ],
        "row-diagnostics-v1.schema.json": [
            "examples/invalid/row-diagnostics-redacted-value.json"
        ],
        "adoption-manifest-v1.schema.json": [
            "examples/invalid/adoption-floating-revision.json"
        ],
        "adoption-manifest-v2.schema.json": [
            "examples/invalid/adoption-v2-floating-revision.json"
        ],
    },
}

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def schema_registry(schemas: dict[str, dict[str, object]]) -> Registry:
    resources = []
    for schema in schemas.values():
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str):
            raise ValueError("every schema must declare a string $id")
        resources.append((schema_id, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def validate_examples(
    schemas: dict[str, dict[str, object]], registry: Registry
) -> list[str]:
    failures: list[str] = []
    for expectation, schema_cases in CASES.items():
        for schema_name, relative_paths in schema_cases.items():
            validator = Draft202012Validator(schemas[schema_name], registry=registry)
            for relative_path in relative_paths:
                instance = load_json(ROOT / relative_path)
                errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
                if expectation == "valid" and errors:
                    failures.append(
                        f"{relative_path} must validate: {errors[0].message}"
                    )
                if expectation == "invalid" and not errors:
                    failures.append(f"{relative_path} must be rejected")
    return failures


def validate_markdown_links() -> list[str]:
    failures: list[str] = []
    for document in ROOT.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            relative_target = target.split("#", 1)[0]
            if relative_target and not (document.parent / relative_target).exists():
                failures.append(
                    f"{document.relative_to(ROOT)} links to missing {target}"
                )
    return failures


def main() -> int:
    schemas = {
        path.name: load_json(path)
        for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
    }
    if set(schemas) != {
        "adoption-manifest-v1.schema.json",
        "adoption-manifest-v2.schema.json",
        "capabilities-v1.schema.json",
        "capabilities-v2.schema.json",
        "cli-envelope-v2.schema.json",
        "error-v1.schema.json",
        "row-diagnostics-v1.schema.json",
    }:
        print("schema inventory differs from the validation contract", file=sys.stderr)
        return 1

    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            print(f"invalid schema {name}: {error}", file=sys.stderr)
            return 1

    registry = schema_registry(schemas)
    failures = validate_examples(schemas, registry)
    failures.extend(validate_markdown_links())
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    valid_count = sum(len(paths) for paths in CASES["valid"].values())
    invalid_count = sum(len(paths) for paths in CASES["invalid"].values())
    print(
        f"validated {len(schemas)} schemas, {valid_count} valid examples and "
        f"{invalid_count} rejected examples"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
