"""Messages without data (decision 0021).

A message of the gate holds only fixed text and structural identifiers: rule
identifiers, paths of repository files, positions, names the validator's code
defines (a reserved metadata key, an error axis, a component), and names of a
contract document (a schema, a catalog, a binding, a Markdown text) quoted
through `contract_name`. Never a value, a key or a name taken from a vector
or an example, not even quoted: those name members by position.
`test_message_sentinels` enforces it on every input of the gate.
"""

from __future__ import annotations

from typing import Any, Iterable

from json_values import same_document


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
        if (name in declared) != (name in expected)
        or (name in declared and not same_document(declared[name], expected[name]))
    ]
    return ", ".join(differing) or "none"


def contract_name(name: Any) -> str:
    """A name read from a contract document, between « and »: the only way
    a message quotes document text. Never pass a value of a vector or an
    example; the sentinel test fails when one arrives here."""
    return "\u00ab" + str(name).replace("\u00ab", "").replace("\u00bb", "") + "\u00bb"
