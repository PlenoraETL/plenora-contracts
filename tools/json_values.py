"""Equality of JSON data by type and by value.

Python's `==` is not JSON equality: `1 == True == 1.0`, `0 == False`, also
inside a list, a tuple or a dictionary, and `{1} == {True}`. A check that
compares two documents, or a document with an expected value, with `==`
takes a `const` 1 changed into `true`, or a version `1` into `1.0`, for the
same value and passes in silence. The tools compare JSON data with
`same_json` and index it with `json_key`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def json_key(value: Any) -> Any:
    """A hashable image of JSON data: two values have the same image only
    when they have the same JSON type and value at every depth. The members
    of an object compare whatever their order, as in JSON; an array and a
    tuple are both arrays. Anything else is not JSON data and raises
    `TypeError`: comparing it would have to guess."""
    if value is None:
        return ("null",)
    kind = type(value)
    if kind is bool:
        return ("boolean", value)
    if kind is int:
        return ("integer", value)
    if kind is float:
        # `repr` tells -0.0 from 0.0; JSON has no NaN nor infinity.
        return ("float", repr(value))
    if kind is Decimal:
        return ("decimal", str(value))
    if kind is str:
        return ("string", value)
    if kind in (list, tuple):
        return ("array", tuple(json_key(item) for item in value))
    if kind is dict:
        members = [(json_key(key), json_key(item)) for key, item in value.items()]
        return ("object", tuple(sorted(members, key=repr)))
    raise TypeError(f"not JSON data: {kind.__name__}")


def same_json(left: Any, right: Any) -> bool:
    """The same JSON data: same types and values at every depth."""
    return json_key(left) == json_key(right)
