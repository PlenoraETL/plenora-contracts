"""Equality of JSON data by type and by value, in two contexts.

Python's `==` is not JSON equality: `1 == True == 1.0`, `0 == False`, also
inside a list, a tuple or a dictionary, and `{1} == {True}`. A check that
compares two documents, or a document with an expected value, with `==`
takes a `const` 1 changed into `true`, or a version `1` into `1.0`, for the
same value and passes in silence.

Numbers are compared in one of two contexts, which every caller names:

- `same_document` / `document_key`: a published document that is not a
  schema assertion (a vector, an example, a catalog, a binding, an expected
  value). COMPATIBILITY.md forbids modifying a published vector, and a
  consumer reads each number as written: the sign of a zero is data (RA-003
  keeps it), and `1.0` against `1.00` is another text. A decimal is
  compared by its exact representation, the coefficient digits and the
  exponent the parser keeps, so only formatting the parser does not keep
  (the exponent letter, `10e-1` against `1.0`) is not a change.
- `same_schema_value` / `schema_value_key`: the numeric assertions of a
  JSON Schema, which compares numbers by value: `1.0`, `1.00` and `1e0`,
  `0.0` and `-0.0` validate the same instances (COMPATIBILITY.md: a schema
  edit that cannot alter validation is compatible).

In both contexts an integer and a decimal stay two values (`1` against
`1.0`), and `1.0` and `1.0000000000000001` two numbers.

Both walk the data with an explicit stack, never by recursion: a document
nested 10,000 levels deep is compared like a flat one, in time linear in its
size (plus the sort of each object's member names for the keys); no subtree
is serialized.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


class _Member:
    """A member name on the stack of `_key`, told apart from the values."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


def _scalar(value: Any, by_value: bool) -> tuple[str, Any] | None:
    """The typed image of a scalar in its context, None for an array or an
    object; anything that is not JSON data raises `TypeError`: comparing it
    would guess."""
    if value is None:
        return ("null", None)
    kind = type(value)
    if kind is bool:
        return ("boolean", value)
    if kind is int:
        return ("integer", value)
    if kind is float:
        if by_value:
            # -0.0 == 0.0 (and they hash alike); a NaN is the same as itself.
            return ("float", value if value == value else "nan")
        # `repr` tells -0.0 from 0.0; a NaN is the same as itself.
        return ("float", repr(value))
    if kind is Decimal:
        return ("decimal", decimal_value(value) if by_value else decimal_representation(value))
    if kind is str:
        return ("string", value)
    if kind in (list, tuple, dict):
        return None
    raise TypeError(f"not JSON data: {kind.__name__}")


def decimal_representation(value: Decimal) -> tuple:
    """The exact representation of a decimal as parsed: sign, coefficient
    digits and exponent, as written (`-0.0`, `1.00` kept)."""
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        # NaN or infinity, which JSON does not have: compared as written.
        return ("special", str(value))
    return (sign, tuple(digits), exponent)


def decimal_value(value: Decimal) -> tuple:
    """The exact value of a decimal, independent of its spelling and of any
    context precision (`Decimal.normalize` would round to 28 digits): sign,
    digits without trailing zeros and exponent; every zero is one value."""
    image = decimal_representation(value)
    if image[0] == "special":
        return image
    sign, digits, exponent = image
    digits = list(digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        return (0, (0,), 0)
    return (sign, tuple(digits), exponent)


def decimal_text(value: Decimal) -> str:
    """A JSON number text of the exact representation of a decimal (the
    digest of a published document): `-0.0` and `0.0`, `1.0` and `1.00`
    have two texts."""
    image = decimal_representation(value)
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


def _same(left: Any, right: Any, by_value: bool) -> bool:
    stack = [(left, right)]
    while stack:
        one, other = stack.pop()
        image = _scalar(one, by_value)
        if image is not None:
            if image != _scalar(other, by_value):
                return False
            continue
        if type(one) is dict:
            if type(other) is not dict or len(one) != len(other):
                _scalar(other, by_value)
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
            _scalar(other, by_value)
            return False
        if len(one) != len(other):
            return False
        stack.extend(zip(one, other))
    return True


def _key(value: Any, by_value: bool) -> tuple:
    tokens: list[tuple] = []
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        if type(item) is _Member:
            tokens.append(("name", item.name))
            continue
        image = _scalar(item, by_value)
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


def same_document(left: Any, right: Any) -> bool:
    """The same published data: same types at every depth and every number
    with its exact representation. The members of an object compare
    whatever their order, as in JSON; an array and a tuple are both arrays."""
    return _same(left, right, False)


def document_key(value: Any) -> tuple:
    """A hashable image of published data: the same image only when
    `same_document` holds. Flat (every array and object states its size),
    so hashing it never recurses."""
    return _key(value, False)


def same_schema_value(left: Any, right: Any) -> bool:
    """The same schema assertions: as `same_document`, but every number by
    its exact value (`1.0 == 1.00 == 1e0`, `0.0 == -0.0`)."""
    return _same(left, right, True)


def schema_value_key(value: Any) -> tuple:
    """A hashable image of schema assertions: the same image only when
    `same_schema_value` holds."""
    return _key(value, True)
