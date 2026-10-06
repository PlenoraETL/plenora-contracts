"""Base of the immutability comparison for a CI event.

Prints the commit `check_schema_immutability.py` compares with, as
`PLENORA_SCHEMA_BASE`:

- a push to `main`: the previous tip of `main` (`EVENT_BEFORE`), also after a
  forced push, so that a rewrite cannot drop what `main` had published;
- a push of a release tag `v*`: the tagged commit, which MUST be a commit of
  `main` (an ancestor of `origin/main`); a release tag elsewhere fails;
- anything else (a pull request, a push to another branch, another tag): the
  commit where the checked revision leaves `main`. The gate also compares the
  documents the branch changed with the current `origin/main`.

Reads `GITHUB_EVENT_NAME`, `GITHUB_REF` and `EVENT_BEFORE`; runs in the
checked-out repository.
"""

from __future__ import annotations

import os
import subprocess
import sys

MAIN = "refs/heads/main"
MAIN_REF = "refs/remotes/origin/main"
NO_COMMIT = "0" * 40


def git(root: str, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", root, *arguments], text=True, stderr=subprocess.PIPE
    ).strip()


def is_ancestor(root: str, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", root, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ValueError(f"cannot compare {ancestor} with {descendant}")
    return result.returncode == 0


def comparison_base(event: str, ref: str, before: str, root: str = ".") -> str:
    if event == "push" and ref == MAIN:
        if not before or before == NO_COMMIT:
            raise ValueError("a push to main has no previous tip")
        return before
    if event == "push" and ref.startswith("refs/tags/v"):
        tagged = git(root, "rev-parse", "HEAD^{commit}")
        if not is_ancestor(root, tagged, MAIN_REF):
            raise ValueError(f"release tag {ref.removeprefix('refs/tags/')} does not point to a commit of main")
        return tagged
    return git(root, "merge-base", "HEAD", MAIN_REF)


def main() -> int:
    try:
        base = comparison_base(
            os.environ.get("GITHUB_EVENT_NAME", ""),
            os.environ.get("GITHUB_REF", ""),
            os.environ.get("EVENT_BEFORE", ""),
        )
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"comparison base: {error}", file=sys.stderr)
        return 1
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
