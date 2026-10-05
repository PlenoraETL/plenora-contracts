"""Null fuzz of the complete gate: every object member of every vector and
example, replaced by null one at a time, must end in a clean verdict (exit 0
or 1 with validation errors), never in an internal validator error.

Documents are parsed once and schema verdicts are memoized per instance, so
each run re-validates only the document it changes.
"""

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import validate_specs as validator

ROOT = validator.ROOT
FUZZED = sorted(
    [*ROOT.glob("vectors/**/*.json"), *ROOT.glob("examples/**/*.json")]
)


def member_paths(value, prefix=()):
    """Every object member, and the members inside the first item of each
    list (the other items have the same shape)."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield prefix + (key,)
            yield from member_paths(child, prefix + (key,))
    elif isinstance(value, list) and value:
        yield from member_paths(value[0], prefix + (0,))


def set_null(document, path):
    node = document
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = None


class NullFuzzTests(unittest.TestCase):
    def test_every_member_null_ends_in_a_clean_verdict(self):
        original_load = validator.load_json
        original_errors = validator.instance_errors
        parsed = {}

        def cached(path):
            # Shared, unchanged documents: the gate must not mutate them, and
            # the end of the test checks that it did not.
            if path not in parsed:
                parsed[path] = original_load(path)
            return parsed[path]

        verdicts = {}
        shared = set()

        def memoized(schema, instance, registry):
            if not shared:
                shared.update(id(document) for document in parsed.values())
            if id(instance) in shared and any(instance is document for document in parsed.values()):
                key = (id(schema), id(instance))
            else:
                key = (id(schema), json.dumps(instance, sort_keys=True))
            if key not in verdicts:
                verdicts[key] = original_errors(schema, instance, registry)
            return list(verdicts[key])

        target = {}

        def mutated(path):
            document = cached(path)
            if path == target.get("path"):
                document = copy.deepcopy(document)
                set_null(document, target["member"])
            return document

        crashes = []
        runs = 0
        with patch.object(validator, "instance_errors", memoized), \
                patch.object(validator.Draft202012Validator, "check_schema", lambda schema: None), \
                patch.object(validator, "validate_markdown_links", lambda: []), \
                patch.object(validator, "load_json", mutated):
            for path in FUZZED:
                for member in list(member_paths(cached(path))):
                    target.update(path=path, member=member)
                    with contextlib.redirect_stdout(io.StringIO()), \
                            contextlib.redirect_stderr(io.StringIO()) as errors:
                        try:
                            status = validator.main()
                        except Exception as error:  # noqa: BLE001 - what the fuzz looks for
                            status = f"{type(error).__name__}: {error}"
                            print(status, file=errors)
                    runs += 1
                    if status not in (0, 1) or "internal validator error" in errors.getvalue():
                        crashes.append(
                            f"{path.relative_to(ROOT).as_posix()} {list(member)}: "
                            + errors.getvalue().strip().splitlines()[-1]
                        )
        self.assertGreater(runs, 1000)
        for path, document in parsed.items():
            self.assertEqual(document, original_load(path), f"the gate mutated {path}")
        self.assertEqual(crashes, [])


if __name__ == "__main__":
    unittest.main()
