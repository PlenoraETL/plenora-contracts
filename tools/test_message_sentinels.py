"""No data in the gate's messages: every string value, number and object key
of every vector and example, replaced one at a time by a sentinel, must
never appear in what the complete gate prints (decision 0021).

A message that names a value, a field, an operation or a key taken from a
document fails this test, whatever validator builds it.
"""

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import validate_specs as validator

ROOT = validator.ROOT
FUZZED = sorted([*ROOT.glob("vectors/**/*.json"), *ROOT.glob("examples/**/*.json")])
TEXT = "ZQXSENTINELQZ"
NUMBER = 731731731
SEEN = (TEXT, str(NUMBER))


def members(value, prefix=()):
    """Every object member, and the members of the first item of each list."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield prefix + (key,)
            yield from members(child, prefix + (key,))
    elif isinstance(value, list) and value:
        yield from members(value[0], prefix + (0,))


def mutations(document, path):
    """The mutated copies of one member: its value, then its key."""
    parent = document
    for step in path[:-1]:
        parent = parent[step]
    last = path[-1]
    value = parent[last]
    if isinstance(value, str):
        yield "value", lambda node: node.__setitem__(last, TEXT + value[:0])
    elif isinstance(value, int) and not isinstance(value, bool):
        yield "number", lambda node: node.__setitem__(last, NUMBER)
    if isinstance(last, str):
        yield "key", lambda node: node.__setitem__(last + TEXT, node.pop(last))


class SentinelTests(unittest.TestCase):
    def test_no_document_content_reaches_a_message(self):
        original_load = validator.load_json
        original_errors = validator.instance_errors
        parsed = {}

        def cached(path):
            if path not in parsed:
                parsed[path] = original_load(path)
            return parsed[path]

        verdicts = {}

        def memoized(schema, instance, registry):
            key = (id(schema), json.dumps(instance, sort_keys=True))
            if key not in verdicts:
                verdicts[key] = original_errors(schema, instance, registry)
            return list(verdicts[key])

        target = {}

        def mutated(path):
            document = cached(path)
            if path == target.get("path"):
                document = copy.deepcopy(document)
                parent = document
                for step in target["member"][:-1]:
                    parent = parent[step]
                target["change"](parent)
            return document

        leaks = []
        runs = 0
        with patch.object(validator, "instance_errors", memoized), \
                patch.object(validator.Draft202012Validator, "check_schema", lambda schema: None), \
                patch.object(validator, "validate_markdown_links", lambda: []), \
                patch.object(validator, "load_json", mutated):
            for path in FUZZED:
                document = cached(path)
                for member in list(members(document)):
                    for kind, change in mutations(document, member):
                        target.update(path=path, member=member, change=change)
                        with contextlib.redirect_stdout(io.StringIO()) as out, \
                                contextlib.redirect_stderr(io.StringIO()) as err:
                            try:
                                validator.main()
                            except Exception as error:  # noqa: BLE001 - reported below
                                print(f"{type(error).__name__}: {error}", file=err)
                        runs += 1
                        printed = out.getvalue() + err.getvalue()
                        if any(sentinel in printed for sentinel in SEEN):
                            line = next(item for item in printed.splitlines() if any(s in item for s in SEEN))
                            leaks.append(f"{path.relative_to(ROOT).as_posix()} {list(member)} {kind}: {line}")
        self.leaks = leaks
        self.assertGreater(runs, 1000)
        self.assertEqual(leaks, [])


if __name__ == "__main__":
    unittest.main()
