"""Equality of JSON data by type and by value.

Python's `==` is not JSON equality: `1 == True == 1.0`, `0 == False`, also
inside a list, a tuple or a dictionary, and `{1} == {True}`. A check that
compares two documents, or a document with an expected value, with `==`
takes a `const` 1 changed into `true`, or a version `1` into `1.0`, for the
same value and passes in silence. The tools compare JSON data with
`same_json` and index it with `json_key`.

Both walk the data with an explicit stack, never by recursion: a document
nested 10,000 levels deep is compared like a flat one, and in time linear in
its size (plus the sort of each object's member names for `json_key`); no
subtree is serialized.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


class _Member:
    """A member name on the stack of `json_key`, told apart from the values."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


def _scalar(value: Any) -> tuple[str, Any] | None:
    """The typed image of a scalar, None for an array or an object; anything
    that is not JSON data raises `TypeError`: comparing it would guess."""
    if value is None:
        return ("null", None)
    kind = type(value)
    if kind is bool:
        return ("boolean", value)
    if kind is int:
        return ("integer", value)
    if kind is float:
        # `repr` tells -0.0 from 0.0; a NaN is the same as itself.
        return ("float", repr(value))
    if kind is Decimal:
        # By exact value: `1.0`, `1.00` and `1e0` are one number
        # (COMPATIBILITY.md), `1.0000000000000001` another.
        return ("decimal", decimal_value(value))
    if kind is str:
        return ("string", value)
    if kind in (list, tuple, dict):
        return None
    raise TypeError(f"not JSON data: {kind.__name__}")


def decimal_value(value: Decimal) -> tuple:
    """The exact value of a decimal, independent of its spelling and of any
    context precision (`Decimal.normalize` would round to 28 digits): sign,
    digits without trailing zeros and exponent; every zero is one value."""
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        # NaN or infinity, which JSON does not have: compared as written.
        return ("special", str(value))
    digits = list(digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        return (0, (0,), 0)
    return (sign, tuple(digits), exponent)


def decimal_text(value: Decimal) -> str:
    """A JSON number text of the exact value of a decimal: two spellings of
    one value have the same text."""
    image = decimal_value(value)
    if image[0] == "special":
        raise TypeError("not JSON data: a decimal that is not a finite number")
    sign, digits, exponent = image
    # Always with an exponent: an integer is never written so, and stays
    # another value (`1` against `1.0`).
    return ("-" if sign else "") + "".join(map(str, digits)) + f"E{exponent}"


def _names(value: dict) -> list[str]:
    for name in value:
        if type(name) is not str:
            raise TypeError("not JSON data: an object member name that is not a string")
    return list(value)


def same_json(left: Any, right: Any) -> bool:
    """The same JSON data: same types and values at every depth. The members
    of an object compare whatever their order, as in JSON; an array and a
    tuple are both arrays."""
    stack = [(left, right)]
    while stack:
        one, other = stack.pop()
        image = _scalar(one)
        if image is not None:
            if image != _scalar(other):
                return False
            continue
        if type(one) is dict:
            if type(other) is not dict or len(one) != len(other):
                _scalar(other)
                return False
            _names(other)
            for name in _names(one):
                # A string name is never equal to a name of another type, so
                # equal sizes and inclusion make the same names.
                if name not in other:
                    return False
                stack.append((one[name], other[name]))
            continue
        if type(other) not in (list, tuple):
            _scalar(other)
            return False
        if len(one) != len(other):
            return False
        stack.extend(zip(one, other))
    return True


def json_key(value: Any) -> tuple:
    """A hashable image of JSON data: two values have the same image only
    when `same_json` holds. The image is flat, a sequence of tokens in which
    every array and object states its size, so hashing it never recurses."""
    tokens: list[tuple] = []
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        if type(item) is _Member:
            tokens.append(("name", item.name))
            continue
        image = _scalar(item)
        if image is not None:
            tokens.append(image)
        elif type(item) is dict:
            names = sorted(_names(item))
            tokens.append(("object", len(names)))
            for name in reversed(names):
                stack.append(item[name])
                stack.append(_Member(name))
        else:
            tokens.append(("array", len(item)))
            stack.extend(reversed(item))
    return tuple(tokens)
