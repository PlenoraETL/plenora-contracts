"""Messages without data (decision 0021).

A message of the gate holds only fixed text and structural identifiers: rule
identifiers, paths of repository files, positions, and names that a schema
or a contract defines (a reserved metadata key, an error axis). Never a
value, a key or a name taken from a vector or an example: those name members
by position. `test_message_sentinels` enforces it on the whole gate.
"""

from __future__ import annotations

from typing import Any, Iterable


def position(index: int) -> str:
    return f"#{index}"


def structural(name: Any, allowed: Iterable[str], index: int) -> str:
    """`name` when the contracts define it, its position otherwise."""
    return name if isinstance(name, str) and name in set(allowed) else position(index)


def differing_members(declared: Any, expected: Any, allowed: Iterable[str]) -> str:
    """The members on which two objects differ, by structural name or
    position; never their values."""
    if not isinstance(declared, dict) or not isinstance(expected, dict):
        return "the whole value"
    allowed = set(allowed)
    names = sorted(set(declared) | set(expected), key=str)
    differing = [
        structural(name, allowed, index)
        for index, name in enumerate(names)
        if declared.get(name, object()) != expected.get(name, object())
    ]
    return ", ".join(differing) or "none"
