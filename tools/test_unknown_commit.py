"""ERR-016 (decision 0020): the cause of an unknown commit outcome decides
its category, in every runtime error vector."""

import unittest

import validate_specs as validator


def payload(**changes):
    base = {"category": "timeout", "phase": "commit", "remote_effect": "unknown",
            "retry": {"kind": "requires_recovery"}, "code": "COMMIT_DEADLINE_ELAPSED"}
    base.update(changes)
    return base


class UnknownCommitTests(unittest.TestCase):
    def test_published_vectors_pass(self):
        errors = validator.validate_runtime_vectors(
            validator.load_catalogs(),
            {path.name: validator.load_json(path) for path in validator.SCHEMA_DIR.glob("*.schema.json")},
            validator.schema_registry(
                {path.name: validator.load_json(path) for path in validator.SCHEMA_DIR.glob("*.schema.json")}
            ),
        )
        self.assertEqual(errors, [])

    def test_each_cause_has_its_category(self):
        self.assertEqual(validator.unknown_commit_errors("v", payload()), [])
        self.assertEqual(validator.unknown_commit_errors("v", payload(category="io", code="COMMIT_CONFIRMATION_LOST")), [])
        self.assertEqual(len(validator.unknown_commit_errors("v", payload(category="internal"))), 1)
        self.assertEqual(validator.unknown_commit_errors("v", payload(code="SOMETHING")), [])
        self.assertEqual(validator.unknown_commit_errors("v", payload(code="CANCELLED", category="cancelled")), [])
        self.assertEqual(len(validator.unknown_commit_errors("v", payload(code="SOMETHING", retry={"kind": "safe"}))), 1)
        self.assertEqual(len(validator.unknown_commit_errors("v", payload(retry={"kind": "safe"}))), 1)

    def test_other_errors_are_not_checked(self):
        self.assertEqual(validator.unknown_commit_errors("v", payload(phase="write", code="X")), [])
        self.assertEqual(validator.unknown_commit_errors("v", payload(remote_effect="none", code="X")), [])


if __name__ == "__main__":
    unittest.main()
