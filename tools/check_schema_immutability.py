"""Compare published contract documents against immutable Git revisions.

Protected: versioned schemas (`schemas/*.schema.json`), public catalogs and
operation registries (`catalogs/*-v<N>.json`), surface binding maps
(`bindings/*-v<N>.json`) and normative vectors (`vectors/**/*.json`).
COMPATIBILITY.md («Immutability of published documents») states which
additions each kind admits; everything else published is fixed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
# The main revision every later check starts from (merge of PR #12,
# 2026-10-05). A branch is also compared with the commit where it left
# `origin/main` (`fork_point`), so a document published after this floor is
# protected on the first push of a branch too.
RATIFIED_BASE = "23fed27d5736e5f32906a0116553fed16a1fb239"
MAIN_REF = "refs/remotes/origin/main"
ANNOTATIONS = {"$comment", "title", "description", "default", "examples", "deprecated", "readOnly", "writeOnly"}
SCHEMA_MAPS = {"$defs", "definitions", "properties", "patternProperties", "dependentSchemas"}
SCHEMA_ARRAYS = {"allOf", "anyOf", "oneOf", "prefixItems"}
SCHEMA_VALUES = {
    "additionalProperties", "unevaluatedProperties", "propertyNames", "contains",
    "additionalItems", "unevaluatedItems", "contentSchema", "not", "if", "then", "else",
}
PROTECTED_DIRECTORIES = ("schemas", "catalogs", "bindings", "vectors")
VERSIONED_FILE = re.compile(r"^(catalogs|bindings)/[a-z0-9-]+-v[1-9][0-9]*\.json$")
# A target surface still open in the base may be selected later (a new public
# surface, COMPATIBILITY.md); a selected applicability is fixed.
OPEN_APPLICABILITY = {"undecided", "not_applicable"}
# Prose a catalog may clarify in place, like schema annotations.
OPERATION_PROSE = {"summary"}


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


class Erratum(NamedTuple):
    """A declared erratum (COMPATIBILITY.md, «Errata before adoption»).

    `before` and `after` are digests of the comparable form (`comparable`);
    `decision` must exist and name the file in its `## Erratum` section;
    `last_base` is the last main revision that published `before`: the
    transition is admitted only against that revision or its ancestors, never
    against a base that already published the correction."""

    before: str
    after: str
    decision: str
    last_base: str


ERRATA: dict[str, Erratum] = {
    "schemas/data-execution-result-v3.schema.json": Erratum(
        "679924dfaf4aa35c69ec7e859b86b4d6857a4dad80427e49c4243e4b64d7e9ab",
        "b5195ecca8f7be5062208ec9e42d77fa2aa8e9b551dd6c7e82cc38abbe42c8c6",
        "decisions/0008-data-run-runtime.md",
        "4c1569d4b7fb7f0b451566b71e0f01165f9d6bcc",
    ),
    "vectors/runtime-v1/data-run-success-v3.json": Erratum(
        "28047084abc9651998208af0461146bfd21ed5636cf2d2e80faecf50c7a333ef",
        "18455d1e2c7f19e8379b6c63c72a4e8538e2da0d7bcd4789765220e2c0672413",
        "decisions/0008-data-run-runtime.md",
        "4c1569d4b7fb7f0b451566b71e0f01165f9d6bcc",
    ),
}


def comparable(relative: str, document: Any) -> Any:
    """What the guard compares: assertions of a schema, the whole document
    of anything else."""
    return assertions(document) if relative.startswith("schemas/") else document


def digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assertions_digest(schema: Any) -> str:
    return digest(assertions(schema))


def strict_json(text: str, relative: str) -> Any:
    """A repeated object key would keep one value in silence and could hide
    a change: it fails the check."""
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError(f"{relative} repeats a JSON object key")
        return dict(pairs)

    return json.loads(text, object_pairs_hook=unique)


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True, encoding="utf-8", stderr=subprocess.PIPE
    )


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ValueError(f"cannot compare revisions {ancestor} and {descendant}")
    return result.returncode == 0


def erratum_errors(relative: str, erratum: Erratum, read_text: Callable[[str], str | None]) -> list[str]:
    """A declaration that cannot be verified admits nothing and fails."""
    if not re.fullmatch(r"[0-9a-f]{40}", erratum.last_base):
        return [f"erratum for {relative} must name a full last base SHA"]
    text = read_text(erratum.decision)
    if text is None:
        return [f"erratum for {relative} names a missing decision {erratum.decision}"]
    section = text.split("\n## Erratum\n", 1)
    if len(section) != 2:
        return [f"erratum for {relative}: {erratum.decision} has no '## Erratum' section"]
    body = section[1].split("\n## ", 1)[0]
    if f"`{Path(relative).name}`" not in body:
        return [f"erratum for {relative}: the '## Erratum' section of {erratum.decision} does not name it"]
    return []


def declared_erratum(
    root: Path, base: str, relative: str, previous: Any, current: Any,
    read_text: Callable[[str], str | None],
) -> bool:
    erratum = ERRATA.get(relative)
    if erratum is None or erratum_errors(relative, erratum, read_text):
        return False
    return (
        (digest(comparable(relative, previous)), digest(comparable(relative, current)))
        == (erratum.before, erratum.after)
        and is_ancestor(root, base, erratum.last_base)
    )


MISSING = object()


def fixed_fields(previous: dict, current: dict, open_fields: set[str], label: str) -> list[str]:
    return [
        f"{label} changes {key}"
        for key in sorted(set(previous) | set(current), key=str)
        if key not in open_fields and previous.get(key, MISSING) != current.get(key, MISSING)
    ]


def entries_by(items: Any, key: Callable[[dict], Any], label: str) -> tuple[dict, list[str]]:
    """Index entries by identity; a repeated identity is ambiguous and fails."""
    if not isinstance(items, list):
        return {}, [f"{label} is not a list"]
    index: dict[Any, dict] = {}
    errors = []
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{label} has an entry that is not an object")
            continue
        identity = key(item)
        if identity in index:
            errors.append(f"{label} repeats {identity}")
        index[identity] = item
    return index, errors


def catalog_changes(previous: dict, current: dict) -> list[str]:
    """New operation identities and new surfaces are compatible additions;
    a published identity keeps every other field."""
    errors = fixed_fields(previous, current, {"operations", "target_surfaces", "status"}, "catalog")
    status = (previous.get("status"), current.get("status"))
    if status[0] != status[1] and status != ("provisional", "normative"):
        errors.append(f"catalog changes status {status[0]} to {status[1]}")
    before_surfaces = previous.get("target_surfaces")
    after_surfaces = current.get("target_surfaces")
    if not isinstance(before_surfaces, dict) or not isinstance(after_surfaces, dict):
        errors.append("catalog target surfaces are not an object")
    else:
        for surface in sorted(set(before_surfaces) | set(after_surfaces)):
            applicability = before_surfaces.get(surface, MISSING)
            if after_surfaces.get(surface, MISSING) != applicability and applicability not in OPEN_APPLICABILITY:
                errors.append(f"catalog changes target surface {surface}")
    key = lambda item: (item.get("id"), item.get("version"))
    before, problems = entries_by(previous.get("operations"), key, "base catalog operations")
    after, current_problems = entries_by(current.get("operations"), key, "catalog operations")
    errors += problems + current_problems
    for identity, operation in before.items():
        label = f"operation {identity[0]}@{identity[1]}"
        if identity not in after:
            errors.append(f"{label} removed")
            continue
        errors += fixed_fields(operation, after[identity], {"surfaces"} | OPERATION_PROSE, label)
        old, new = operation.get("surfaces"), after[identity].get("surfaces")
        if not isinstance(old, list) or not isinstance(new, list) or not set(old) <= set(new):
            errors.append(f"{label} drops a surface")
    return errors


def registry_changes(previous: dict, current: dict) -> list[str]:
    """A registry version may gain kernels; a listed kernel keeps its entry."""
    errors = fixed_fields(previous, current, {"operations"}, "registry")
    key = lambda item: item.get("id")
    before, problems = entries_by(previous.get("operations"), key, "base registry operations")
    after, current_problems = entries_by(current.get("operations"), key, "registry operations")
    errors += problems + current_problems
    for identity, entry in before.items():
        if identity not in after:
            errors.append(f"kernel {identity} removed")
        elif after[identity] != entry:
            errors.append(f"kernel {identity} changes")
    return errors


def binding_changes(previous: dict, current: dict) -> list[str]:
    """A binding map may name a surface artifact that was absent, add
    discovery entrypoints and bind new operation versions; a published
    binding keeps its requirement and spellings."""
    errors = fixed_fields(previous, current, {"components"}, "binding map")
    component_key = lambda item: item.get("component")
    before, problems = entries_by(previous.get("components"), component_key, "base binding sections")
    after, current_problems = entries_by(current.get("components"), component_key, "binding sections")
    errors += problems + current_problems
    for component, section in before.items():
        if component not in after:
            errors.append(f"binding section {component} removed")
            continue
        new = after[component]
        errors += fixed_fields(section, new, {"artifact", "discovery", "bindings"}, component)
        if section.get("artifact") is not None and new.get("artifact") != section.get("artifact"):
            errors.append(f"{component} changes its artifact")
        old_discovery, new_discovery = section.get("discovery"), new.get("discovery")
        if (
            not isinstance(old_discovery, list) or not isinstance(new_discovery, list)
            or not set(old_discovery) <= set(new_discovery)
        ):
            errors.append(f"{component} drops a discovery entrypoint")
        key = lambda item: (item.get("operation"), item.get("version"))
        old_bindings, problems = entries_by(section.get("bindings"), key, f"base {component} bindings")
        new_bindings, current_problems = entries_by(new.get("bindings"), key, f"{component} bindings")
        errors += problems + current_problems
        for identity, binding in old_bindings.items():
            if identity not in new_bindings:
                errors.append(f"{component} binding {identity[0]}@{identity[1]} removed")
            elif new_bindings[identity] != binding:
                errors.append(f"{component} binding {identity[0]}@{identity[1]} changes")
    return errors


def document_changes(relative: str, previous: Any, current: Any) -> list[str]:
    """The kind is decided by the base document; a protected document of no
    recognized kind is compared whole (fail closed)."""
    if relative.startswith("schemas/"):
        return [] if assertions(previous) == assertions(current) else ["assertions changed"]
    if isinstance(previous, dict) and isinstance(current, dict):
        contract = previous.get("contract")
        if relative.startswith("catalogs/") and contract == "plenora-public-catalog-v1":
            return catalog_changes(previous, current)
        if relative.startswith("catalogs/") and contract == "plenora-operation-registry-v1":
            return registry_changes(previous, current)
        if relative.startswith("bindings/") and contract == "plenora-surface-bindings-v1":
            return binding_changes(previous, current)
    return [] if previous == current else ["document changed"]


def is_protected(relative: str) -> bool:
    if relative.startswith("schemas/"):
        return relative.endswith(".schema.json") and relative.count("/") == 1
    if relative.startswith("vectors/"):
        return relative.endswith(".json")
    return VERSIONED_FILE.fullmatch(relative) is not None


def check(
    root: Path, base: str, head: str | None = None, touched_since: str | None = None
) -> list[str]:
    """Differences of the working tree (or of revision `head`) from `base`.

    With `touched_since`, only the documents the checked tree changed since
    that revision are compared: `base` is then the current `origin/main`,
    newer than where a branch left it, and a document the branch did not
    touch takes `main`'s content when the branch is merged.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("baseline must be a full immutable commit SHA")
    listed = git(root, "ls-tree", "-r", "--name-only", base, "--", *PROTECTED_DIRECTORIES).splitlines()
    paths = [path for path in listed if is_protected(path)]
    if not any(path.startswith("schemas/") for path in paths):
        raise ValueError("baseline contains no versioned schemas")

    # The working tree is listed by Git, case-sensitively: on a
    # case-insensitive file system a renamed `X.json` would still open under
    # its old spelling and hide the removal.
    present = worktree_paths(root) if head is None else None

    def read_text(relative: str) -> str | None:
        if present is not None and relative.split("/", 1)[0] in PROTECTED_DIRECTORIES:
            return (root / relative).read_text(encoding="utf-8") if relative in present else None
        if present is not None:
            # A decision of an erratum: informative, read as it is on disk.
            path = root / relative
            return path.read_text(encoding="utf-8") if path.is_file() else None
        try:
            return git(root, "show", f"{head}:{relative}")
        except subprocess.CalledProcessError:
            return None

    def untouched(relative: str) -> bool:
        if touched_since is None:
            return False
        try:
            before = git(root, "show", f"{touched_since}:{relative}")
        except subprocess.CalledProcessError:
            before = None
        return read_text(relative) == before

    errors = []
    # Every declaration for a document this base or tree publishes must be
    # verifiable; one for a document neither carries is inert.
    for relative, erratum in sorted(ERRATA.items()):
        if untouched(relative):
            continue
        if relative in paths or read_text(relative) is not None:
            errors += erratum_errors(relative, erratum, read_text)
    for relative in paths:
        if untouched(relative):
            continue
        text = read_text(relative)
        kind = "schema" if relative.startswith("schemas/") else "document"
        if text is None:
            errors.append(f"published {kind} removed: {relative}")
            continue
        previous = strict_json(git(root, "show", f"{base}:{relative}"), relative)
        current = strict_json(text, relative)
        changes = document_changes(relative, previous, current)
        if not changes or declared_erratum(root, base, relative, previous, current, read_text):
            continue
        if kind == "schema":
            errors.append(f"published schema assertions changed: {relative}; introduce a new version")
        else:
            errors.extend(
                f"published document changed: {relative}: {change}; introduce a new version"
                for change in changes
            )
    if present is not None:
        schema_files = sorted(path for path in present if path.startswith("schemas/") and is_protected(path))
    else:
        listed = git(root, "ls-tree", "-r", "--name-only", head, "--", "schemas").splitlines()
        schema_files = [path for path in listed if is_protected(path)]
    identifiers = set()
    for relative in schema_files:
        document = strict_json(read_text(relative) or "null", relative)
        identifier = document.get("$id") if isinstance(document, dict) else None
        if not isinstance(identifier, str) or identifier in identifiers:
            errors.append(f"missing or duplicate schema identifier: {Path(relative).name}")
        if isinstance(identifier, str):
            identifiers.add(identifier)
    return errors


def worktree_paths(root: Path) -> set[str]:
    """Files of the working tree under the protected directories, with the
    exact spelling they have on disk.

    Git lists the candidates: tracked files, and every untracked file under
    the protected directories, ignored ones included (an ignored schema is
    still a schema). Each candidate counts only if every component of its
    path exists on disk with exactly that spelling: a case-only rename made
    on a case-insensitive file system, which the index does not record,
    leaves the old spelling openable but absent from its directory listing.
    """
    def listed(*options: str) -> set[str]:
        output = git(root, "ls-files", "-z", *options, "--", *PROTECTED_DIRECTORIES)
        return {path for path in output.split("\0") if path}

    listings: dict[Path, set[str]] = {}

    def spelled_on_disk(relative: str) -> bool:
        directory = root
        for part in relative.split("/"):
            if directory not in listings:
                try:
                    listings[directory] = set(os.listdir(directory))
                except OSError:
                    listings[directory] = set()
            if part not in listings[directory]:
                return False
            directory = directory / part
        return directory.is_file()

    candidates = (listed("--cached") | listed("--others")) - listed("--deleted")
    return {path for path in candidates if spelled_on_disk(path)}


# Local opt-out when no `origin/main` exists (a clone without that remote).
# Never honored in CI: any of `CI_MARKERS` set, with any value, disables it.
NO_FORK_POINT_WAIVER = "PLENORA_ALLOW_NO_FORK_POINT"
CI_MARKERS = ("CI", "GITHUB_ACTIONS", "GITHUB_RUN_ID")


def fork_point(root: Path) -> str:
    """Where HEAD left `origin/main`. Without it a document published after
    the ratified floor would go unchecked on a branch's first push, so its
    absence fails the check."""
    try:
        return git(root, "merge-base", "HEAD", MAIN_REF).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"cannot find where HEAD left {MAIN_REF}") from error


def stale_main_error(root: Path) -> str | None:
    """`origin/main` as the remote has it now. A runner with an older
    `origin/main` would compare with a main that has since moved, and skip
    what was published in between, so CI fails instead."""
    try:
        local = git(root, "rev-parse", MAIN_REF).strip()
        listed = git(root, "ls-remote", "origin", "refs/heads/main").split()
    except (OSError, subprocess.CalledProcessError):
        return "cannot read refs/heads/main from origin"
    if not listed:
        return "origin has no refs/heads/main"
    if listed[0] != local:
        return (
            f"{MAIN_REF} is {local[:12]} but origin's main is {listed[0][:12]}; "
            "fetch origin main before checking"
        )
    return None


def in_ci() -> bool:
    return any(marker in os.environ for marker in CI_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("PLENORA_SCHEMA_BASE"))
    arguments = parser.parse_args()
    base = arguments.base
    if not base or base == "0" * 40:
        base = None
    try:
        fork = fork_point(ROOT)
    except ValueError as error:
        waived = os.environ.get(NO_FORK_POINT_WAIVER) == "1" and not any(
            marker in os.environ for marker in CI_MARKERS
        )
        if not waived:
            print(f"published document baseline check failed: {error}; fetch it, or set "
                  f"{NO_FORK_POINT_WAIVER}=1 outside CI to check only the floor and the event base")
            return 1
        fork = None
        print(f"note: {error}; {NO_FORK_POINT_WAIVER}=1, checked against the ratified floor and the event base only")
    if fork is not None and in_ci():
        stale = stale_main_error(ROOT)
        if stale is not None:
            print(f"published document baseline check failed: {stale}")
            return 1
    try:
        # The ratified floor remains protected even when a branch's prior push
        # already contained an invalid edit; the fork point protects what main
        # published after the floor; the event base protects newer documents.
        errors = []
        for revision in dict.fromkeys(item for item in (RATIFIED_BASE, fork, base) if item):
            errors.extend(check(ROOT, revision))
        # What main has published since the branch left it: a document the
        # branch also changed is compared with main's current content, so an
        # old branch cannot rewrite it unseen.
        if fork is not None:
            tip = git(ROOT, "rev-parse", MAIN_REF).strip()
            if tip not in (fork, base):
                errors.extend(check(ROOT, tip, touched_since=fork))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"published document baseline check failed: {error}")
        return 1
    if errors:
        for error in errors:
            print(error)
        return 1
    print("published schemas, catalogs, binding maps and vectors unchanged; new schema identifiers are unique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
