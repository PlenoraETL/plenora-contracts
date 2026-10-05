"""Every specification under `specs/` is listed among the README's normative
sources. DATA-PLAN-1.0 was normative and missing from the list."""

import unittest

import validate_specs as validator

README = """# Title

## Normative sources

- [one](specs/a/ONE-1.0.md);
- [two](specs/b/TWO-1.0.md#section).

## Scope
"""


class NormativeIndexTests(unittest.TestCase):
    def test_every_listed_specification_passes(self):
        self.assertEqual(
            validator.normative_index_errors(README, ["specs/a/ONE-1.0.md", "specs/b/TWO-1.0.md"]),
            [],
        )

    def test_unlisted_specification_is_rejected(self):
        errors = validator.normative_index_errors(
            README, ["specs/a/ONE-1.0.md", "specs/data/DATA-PLAN-1.0.md"]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("specs/data/DATA-PLAN-1.0.md", errors[0])

    def test_link_outside_the_section_does_not_count(self):
        readme = README + "\nSee [three](specs/c/THREE-1.0.md).\n"
        errors = validator.normative_index_errors(readme, ["specs/c/THREE-1.0.md"])
        self.assertEqual(len(errors), 1)

    def test_section_at_the_end_of_the_readme_is_read(self):
        readme = "# Title\n\n## Normative sources\n\n- [one](specs/a/ONE-1.0.md).\n"
        self.assertEqual(validator.normative_index_errors(readme, ["specs/a/ONE-1.0.md"]), [])

    def test_missing_section_is_rejected(self):
        self.assertEqual(
            len(validator.normative_index_errors("# Title\n\n## Scope\n", [])), 1
        )

    def test_repository_readme_lists_every_specification(self):
        self.assertEqual(validator.validate_normative_index(), [])


if __name__ == "__main__":
    unittest.main()
