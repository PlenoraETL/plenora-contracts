#!/usr/bin/env python3
"""Fail-closed release-input validation for the Plenora conformance campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__:
    from ._shared import write_json_atomic
    from .release_authority import TRUSTED_INVENTORIES
else:
    from _shared import write_json_atomic
    from release_authority import TRUSTED_INVENTORIES


SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_GATE_ID = "plenora-release-inputs-v1"
EXPECTED_CONTRACTS_REVISION = "e81c3ce7941bacbdb0e083f03c512ae22a6b924a"
EXPECTED_COMPONENT_NAMES = set(next(iter(TRUSTED_INVENTORIES.values())))


class ReleaseVerificationError(RuntimeError):
    """The remote release shape cannot establish a trustworthy observation."""


def _mapping(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _release_identity(component: dict[str, Any]) -> dict[str, Any]:
    return {
        field: component.get(field)
        for field in (
            "name",
            "repository",
            "tag",
            "tag_object",
            "revision",
            "release",
            "source_archive",
            "crates_publish",
        )
    }


def validate_manifest(manifest: object) -> list[str]:
    errors: list[str] = []
    root = _mapping(manifest)
    if root is None:
        return ["manifest must be an object"]

    if root.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EXPECTED_SCHEMA_VERSION}")
    if root.get("gate_id") != EXPECTED_GATE_ID:
        errors.append(f"gate_id must be {EXPECTED_GATE_ID!r}")

    inventory_id = root.get("inventory_id")
    authority = TRUSTED_INVENTORIES.get(inventory_id)
    if authority is None:
        errors.append(
            "inventory_id must select a trusted authority profile: "
            f"{sorted(TRUSTED_INVENTORIES)!r}"
        )

    contracts = _mapping(root.get("contracts"))
    if contracts is None:
        errors.append("contracts must be an object")
    else:
        if contracts.get("revision") != EXPECTED_CONTRACTS_REVISION:
            errors.append(
                "contracts.revision must match the pinned authority "
                f"{EXPECTED_CONTRACTS_REVISION}"
            )
        if not isinstance(contracts.get("icd"), str) or not contracts["icd"]:
            errors.append("contracts.icd must be a non-empty string")

    components = root.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty array")
        return errors

    seen_names: set[str] = set()
    for index, value in enumerate(components):
        prefix = f"components[{index}]"
        component = _mapping(value)
        if component is None:
            errors.append(f"{prefix} must be an object")
            continue

        name = component.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}.name must be a non-empty string")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate component name {name!r}")
        else:
            seen_names.add(name)

        repository = component.get("repository")
        if (
            not isinstance(repository, str)
            or repository.count("/") != 1
            or repository.startswith("/")
            or repository.endswith("/")
        ):
            errors.append(f"{prefix}.repository must be owner/repository")

        tag = component.get("tag")

        for field in ("tag_object", "revision"):
            if not SHA1_RE.fullmatch(str(component.get(field, ""))):
                errors.append(f"{prefix}.{field} must be a lowercase 40-hex SHA")

        release = _mapping(component.get("release"))
        if release is None:
            errors.append(f"{prefix}.release must be an object")
        else:
            if not isinstance(release.get("id"), int) or release["id"] <= 0:
                errors.append(f"{prefix}.release.id must be a positive integer")
            expected_url = (
                f"https://github.com/{repository}/releases/tag/{tag}"
                if isinstance(repository, str) and isinstance(tag, str)
                else None
            )
            if release.get("url") != expected_url:
                errors.append(f"{prefix}.release.url does not match repository/tag")
            if release.get("draft") is not False:
                errors.append(f"{prefix}.release.draft must be false")
            if release.get("prerelease") is not False:
                errors.append(f"{prefix}.release.prerelease must be false")

        archive = _mapping(component.get("source_archive"))
        if archive is None:
            errors.append(f"{prefix}.source_archive must be an object")
        else:
            if not SHA256_RE.fullmatch(str(archive.get("sha256", ""))):
                errors.append(
                    f"{prefix}.source_archive.sha256 must be lowercase 64-hex"
                )
            if not isinstance(archive.get("bytes"), int) or archive["bytes"] <= 0:
                errors.append(f"{prefix}.source_archive.bytes must be positive")

        if component.get("crates_publish") is not False:
            errors.append(f"{prefix}.crates_publish must be false")

        trusted = authority.get(name) if authority is not None else None
        if trusted is None or _release_identity(component) != trusted:
            errors.append(
                f"{prefix} does not match trusted authority {inventory_id!r}"
            )

    if seen_names != EXPECTED_COMPONENT_NAMES:
        missing = sorted(EXPECTED_COMPONENT_NAMES - seen_names)
        extra = sorted(seen_names - EXPECTED_COMPONENT_NAMES)
        errors.append(
            f"component set mismatch: missing={missing!r}, extra={extra!r}"
        )

    return errors


def validate_observation(expected: object, observed: object) -> list[str]:
    errors: list[str] = []
    expected_map = _mapping(expected)
    observed_map = _mapping(observed)
    if expected_map is None or observed_map is None:
        return ["expected and observed release records must be objects"]

    for field in ("tag", "tag_object", "revision"):
        if observed_map.get(field) != expected_map.get(field):
            errors.append(
                f"{field} mismatch: expected {expected_map.get(field)!r}, "
                f"observed {observed_map.get(field)!r}"
            )

    for group, fields in (
        ("release", ("id", "url", "draft", "prerelease")),
        ("source_archive", ("sha256", "bytes")),
    ):
        expected_group = _mapping(expected_map.get(group)) or {}
        observed_group = _mapping(observed_map.get(group)) or {}
        for field in fields:
            if observed_group.get(field) != expected_group.get(field):
                errors.append(
                    f"{group}.{field} mismatch: expected "
                    f"{expected_group.get(field)!r}, observed "
                    f"{observed_group.get(field)!r}"
                )

    return errors


def collect_observation(
    component: dict[str, Any],
    *,
    api_json: Callable[[str], dict[str, Any]],
    api_bytes: Callable[[str], bytes],
) -> dict[str, Any]:
    repository = component.get("repository")
    tag = component.get("tag")
    if not isinstance(repository, str) or not isinstance(tag, str):
        raise ReleaseVerificationError("component repository and tag are required")

    ref_endpoint = f"repos/{repository}/git/ref/tags/{tag}"
    ref = _mapping(api_json(ref_endpoint))
    ref_object = _mapping(ref.get("object") if ref is not None else None)
    if ref_object is None or ref_object.get("type") != "tag":
        raise ReleaseVerificationError(
            f"{repository}@{tag} must be an annotated tag"
        )
    tag_object = ref_object.get("sha")
    if not isinstance(tag_object, str):
        raise ReleaseVerificationError(f"{repository}@{tag}: tag object SHA missing")

    tag_endpoint = f"repos/{repository}/git/tags/{tag_object}"
    tag_record = _mapping(api_json(tag_endpoint))
    peeled_object = _mapping(
        tag_record.get("object") if tag_record is not None else None
    )
    if peeled_object is None or peeled_object.get("type") != "commit":
        raise ReleaseVerificationError(
            f"{repository}@{tag}: annotated tag must peel directly to a commit"
        )
    revision = peeled_object.get("sha")
    if not isinstance(revision, str):
        raise ReleaseVerificationError(f"{repository}@{tag}: peeled commit SHA missing")

    release_endpoint = f"repos/{repository}/releases/tags/{tag}"
    release_record = _mapping(api_json(release_endpoint))
    if release_record is None:
        raise ReleaseVerificationError(f"{repository}@{tag}: release object missing")

    archive_endpoint = f"repos/{repository}/tarball/{tag}"
    archive = api_bytes(archive_endpoint)
    if not isinstance(archive, bytes):
        raise ReleaseVerificationError(
            f"{repository}@{tag}: source archive API did not return bytes"
        )

    return {
        "tag": release_record.get("tag_name"),
        "tag_object": tag_object,
        "revision": revision,
        "release": {
            "id": release_record.get("id"),
            "url": release_record.get("html_url"),
            "draft": release_record.get("draft"),
            "prerelease": release_record.get("prerelease"),
        },
        "source_archive": {
            "sha256": hashlib.sha256(archive).hexdigest(),
            "bytes": len(archive),
        },
    }


def verify_releases(
    manifest: object,
    collector: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    manifest_errors = validate_manifest(manifest)
    report: dict[str, Any] = {
        "gate_id": EXPECTED_GATE_ID,
        "status": "fail" if manifest_errors else "pass",
        "manifest_errors": manifest_errors,
        "components": [],
    }
    if manifest_errors:
        return report

    root = _mapping(manifest)
    assert root is not None
    components = root["components"]
    assert isinstance(components, list)

    for value in components:
        component = _mapping(value)
        assert component is not None
        errors: list[str] = []
        observed: dict[str, Any] | None = None
        try:
            observed = collector(component)
            errors.extend(validate_observation(component, observed))
        except Exception as exc:  # API/process failures are gate evidence, not crashes.
            errors.append(f"collection failed: {type(exc).__name__}: {exc}")

        report["components"].append(
            {
                "name": component.get("name"),
                "repository": component.get("repository"),
                "expected_revision": component.get("revision"),
                "observed": observed,
                "errors": errors,
                "status": "fail" if errors else "pass",
            }
        )
        if errors:
            report["status"] = "fail"

    return report


def _gh_api_bytes(endpoint: str) -> bytes:
    completed = subprocess.run(
        ["gh", "api", endpoint],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace")[:2000]
        raise ReleaseVerificationError(
            f"gh api {endpoint!r} exited {completed.returncode}: {diagnostic}"
        )
    return completed.stdout


def _gh_api_json(endpoint: str) -> dict[str, Any]:
    payload = _gh_api_bytes(endpoint)
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseVerificationError(
            f"gh api {endpoint!r} returned invalid UTF-8 JSON: {exc}"
        ) from exc
    mapping = _mapping(value)
    if mapping is None:
        raise ReleaseVerificationError(
            f"gh api {endpoint!r} returned a non-object JSON value"
        )
    return mapping


def main(
    argv: list[str] | None = None,
    *,
    api_json: Callable[[str], dict[str, Any]] | None = None,
    api_bytes: Callable[[str], bytes] | None = None,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report: dict[str, Any] = {
            "gate_id": EXPECTED_GATE_ID,
            "status": "fail",
            "manifest_errors": [f"cannot read manifest: {type(exc).__name__}: {exc}"],
            "components": [],
        }
    else:
        json_reader = api_json or _gh_api_json
        bytes_reader = api_bytes or _gh_api_bytes
        report = verify_releases(
            manifest,
            lambda component: collect_observation(
                component,
                api_json=json_reader,
                api_bytes=bytes_reader,
            ),
        )

    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(encoded)
    write_json_atomic(args.json_out, report)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
