"""Run discovered gate tests, with an explicit quick selection for automatic CI.

The complete discovery remains the default. Exhaustive mutation campaigns run
in the manual coverage workflow; their harness unit tests stay in quick CI.
"""

import argparse
from pathlib import Path
import unittest

LONG_TESTS = frozenset({
    "test_null_fuzz.NullFuzzTests.test_every_member_null_ends_in_a_clean_verdict",
    "test_message_sentinels.SentinelTests.test_no_input_reaches_a_message",
})


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def select(suite, quick=False):
    tests = list(cases(suite))
    missing = LONG_TESTS - {test.id() for test in tests}
    if missing:
        raise ValueError(f"campaigns absent from discovery: {sorted(missing)}")
    return unittest.TestSuite(test for test in tests if not quick or test.id() not in LONG_TESTS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py")
    selected = select(suite, args.quick)
    print(f"Selected {selected.countTestCases()} tests; manual campaigns: {len(LONG_TESTS) if args.quick else 0}", flush=True)
    return 0 if unittest.TextTestRunner(verbosity=2).run(selected).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
