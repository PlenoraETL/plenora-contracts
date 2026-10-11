"""Null fuzz of the complete gate: every object member and every array
element of every JSON input of the gate (vectors, examples, schemas,
catalogs, bindings, composition), replaced by null one at a time, must end
in a clean verdict (exit 0 or 1 with validation errors), never in an
internal validator error.

The inputs are every JSON file the unmutated gate reads, found by
`gate_fuzz`, which also memoizes what a mutation cannot change.
"""

import unittest

import gate_fuzz
from gate_fuzz import ROOT


def nulled(document, member):
    import copy

    mutated = copy.deepcopy(document)
    node = mutated
    for step in member[:-1]:
        node = node[step]
    node[member[-1]] = None
    return mutated


class NullFuzzTests(unittest.TestCase):
    def test_every_member_null_ends_in_a_clean_verdict(self):
        crashes = []
        runs = 0
        with gate_fuzz.Gate() as gate:
            self.assertEqual(gate.baseline_output[0], 0, gate.baseline_output[1])
            for path in gate.inputs():
                if path.suffix != ".json":
                    continue
                document = gate_fuzz.parse(gate.original[path].decode("utf-8"))
                for member in gate_fuzz.members(document):
                    status, printed = gate.run((path, gate_fuzz.serialize(nulled(document, member))))
                    runs += 1
                    if status not in (0, 1) or "internal validator error" in printed:
                        crashes.append(
                            f"{path.relative_to(ROOT).as_posix()} {list(member)}: "
                            + (printed.strip().splitlines() or [str(status)])[-1]
                        )
            self.assertEqual(gate.check_unmutated(), [])
        self.assertGreater(runs, 5000)
        self.assertEqual(crashes, [])


if __name__ == "__main__":
    unittest.main()
