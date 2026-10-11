"""No data in the gate's messages (decision 0021).

Every input of the gate, found by intercepting every read of the unmutated
run (vectors, examples, schemas, catalogs, bindings, composition, Markdown),
is mutated one place at a time: every string value, every object key, every
number and every array element, at any depth; in Markdown every line and
every link target. Strings get up to three sentinels, so that at least one
passes the pattern of the place it occupies and reaches the checks after the
schema: upper case, lower case, and the original value with its last
alphanumeric run replaced. Numbers get an integer, a float and values beyond
the signed and unsigned 64-bit ranges.

The complete gate runs once per mutation. A sentinel must never appear in
what it prints. The only exception is a name of a contract document (a
schema, a catalog, a binding, a Markdown text) that a message quotes through
`messages.contract_name`, between « and »; a value of a vector or an example
is never quoted, not even that way.
"""

from __future__ import annotations

import copy
import re
import unittest
from typing import Any, Iterator

import gate_fuzz
from gate_fuzz import ROOT, Raw

TEXT = "ZQXSENTINELQZ"
LOWER = TEXT.lower()
NUMBERS = ("731731731", "731731.731", "9223372036854775808", "-9223372036854775809", "18446744073709551616")
FOUND = (LOWER, *NUMBERS)
QUOTED = re.compile(r"«[^«»]*»")
ALNUM = re.compile(r"[A-Za-z0-9]+")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def string_sentinels(value: str) -> list[str]:
    runs = list(ALNUM.finditer(value))
    shaped = value[: runs[-1].start()] + LOWER + value[runs[-1].end():] if runs else LOWER
    return list(dict.fromkeys((TEXT, LOWER, shaped)))


def _at(document: Any, member: tuple[Any, ...]) -> Any:
    for step in member:
        document = document[step]
    return document


def json_mutations(document: Any) -> Iterator[tuple[str, Any]]:
    for member in gate_fuzz.members(document):
        last = member[-1]
        value = _at(document, member)
        variants: list[Any] = []
        if isinstance(value, str):
            variants = string_sentinels(value)
        elif isinstance(value, Raw):
            variants = [Raw(number) for number in NUMBERS]
        for variant in variants:
            mutated = copy.deepcopy(document)
            _at(mutated, member[:-1])[last] = variant
            yield f"{list(member)} value", mutated
        if isinstance(last, str):
            for suffix in (TEXT, LOWER):
                mutated = copy.deepcopy(document)
                target = _at(mutated, member[:-1])
                items = list(target.items())
                target.clear()
                target.update((key + suffix if key == last else key, item) for key, item in items)
                yield f"{list(member)} key", mutated


def markdown_mutations(text: str) -> Iterator[tuple[str, str]]:
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if ALNUM.search(line):
            yield f"line {index + 1}", "\n".join(lines[:index] + [ALNUM.sub(LOWER, line)] + lines[index + 1:])
    for match in LINK.finditer(text):
        yield f"link at {match.start(1)}", text[: match.start(1)] + LOWER + ".md" + text[match.end(1):]


def mutations(path, content: bytes) -> Iterator[tuple[str, bytes]]:
    if path.suffix == ".json":
        for kind, document in json_mutations(gate_fuzz.parse(content.decode("utf-8"))):
            yield kind, gate_fuzz.serialize(document)
    elif path.suffix == ".md":
        for kind, text in markdown_mutations(content.decode("utf-8")):
            yield kind, text.encode("utf-8")
    else:
        raise AssertionError(f"an input of the gate the sentinels do not know how to mutate: {path.suffix}")


def leak(printed: str, data: bool) -> str | None:
    visible = printed if data else QUOTED.sub("", printed)
    for line in visible.lower().splitlines():
        if any(token in line for token in FOUND):
            return line
    return None


class SentinelTests(unittest.TestCase):
    def test_no_input_reaches_a_message(self):
        leaks: list[str] = []
        runs = 0
        with gate_fuzz.Gate() as gate:
            self.assertEqual(gate.baseline_output[0], 0, gate.baseline_output[1])
            self.assertEqual(gate.check_equivalence(), [])
            inputs = gate.inputs()
            for path in inputs:
                data = gate_fuzz.is_data(path)
                for kind, content in mutations(path, gate.original[path]):
                    status, printed = gate.run((path, content))
                    runs += 1
                    if runs % 97 == 0:
                        # The oracle: the memoized run prints what a complete one does.
                        self.assertEqual((status, printed), gate.run_complete((path, content)),
                                         f"{path.relative_to(ROOT).as_posix()} {kind}")
                    found = leak(printed, data)
                    if found is not None:
                        leaks.append(f"{path.relative_to(ROOT).as_posix()} {kind}: {found}")
            self.assertEqual(gate.check_unmutated(), [])
        groups = {path.relative_to(ROOT).parts[0] for path in inputs}
        for group in ("vectors", "examples", "schemas", "catalogs", "bindings", "composition", "profiles", "specs"):
            self.assertIn(group, groups)
        self.assertGreater(runs, 10000)
        self.assertEqual(leaks, [])

    def test_the_sentinels(self):
        self.assertEqual(string_sentinels("database.query"), [TEXT, LOWER, "database." + LOWER])
        self.assertEqual(string_sentinels("x"), [TEXT, LOWER])
        self.assertEqual(string_sentinels("--"), [TEXT, LOWER])
        self.assertIsNone(leak("ERROR: «zqxsentinelqz» lacks a member", data=False))
        self.assertIsNotNone(leak("ERROR: «zqxsentinelqz» lacks a member", data=True))
        self.assertIsNotNone(leak("ERROR: 731731.731 is out of range", data=False))
        document = gate_fuzz.parse('{"a": [1, {"b": "c"}], "d": 1.50}')
        kinds = [kind for kind, _ in json_mutations(document)]
        self.assertIn("['a', 0] value", kinds)
        self.assertIn("['a', 1, 'b'] value", kinds)
        self.assertIn("['d'] value", kinds)
        self.assertEqual(gate_fuzz.serialize(document).decode("utf-8"),
                         '{\n  "a": [\n    1,\n    {\n      "b": "c"\n    }\n  ],\n  "d": 1.50\n}\n')
        self.assertEqual(len(list(markdown_mutations("a [x](y.md)\n\n#"))), 2)


if __name__ == "__main__":
    unittest.main()
