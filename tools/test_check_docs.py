"""Counterexamples for documentation links, commands, examples and scope."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_docs as gate


class DocumentationGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_scope_excludes_immutable_trees_but_includes_nested_specs(self):
        included = ["README.md", "decisions/a.md", "specs/catalogs/a.md",
                    "specs/composition/a.md", "proposals/a.md", "conformance/a.md"]
        excluded = [f"{name}/README.md" for name in gate.IMMUTABLE_DIRECTORIES]
        excluded += ["tools/a.md", "examples/a.md", "templates/a.md",
                     "specs/__pycache__/a.md"]
        for name in included:
            self.write(name, "# Valid\n")
        for name in excluded:
            self.write(name, "[broken](missing.md)\n```python\ninvalid(\n")
        count, errors = gate.scan(self.root)
        self.assertEqual(count, len(included))
        self.assertEqual(errors, [])

    def test_links_and_duplicate_anchors(self):
        self.write("specs/target.md", "# Heading\n# Heading\n## Other title\n")
        self.write("README.md",
                   "[first](specs/target.md#heading)\n"
                   "[second](specs/target.md#heading-1)\n"
                   "[encoded](specs/target.md#other%20title)\n"
                   "[missing](missing.md)\n"
                   "[anchor](specs/target.md#absent)\n"
                   "[external](https://example.invalid)\n")
        _, errors = gate.scan(self.root)
        self.assertEqual(len(errors), 3)
        self.assertEqual(sum("anchor inesistente" in v.reason for v in errors), 2)
        self.assertEqual(sum("link locale inesistente" in v.reason for v in errors), 1)

    def test_relative_and_same_document_links(self):
        self.write("README.md", "# Root\n")
        self.write("specs/a.md", "# Local\n[root](../README.md#root)\n[local](#local)\n")
        self.assertEqual(gate.scan(self.root)[1], [])

    def test_commands_must_exist_and_use_tools(self):
        self.write("tools/valid.py", "")
        self.write("scripts/legacy.py", "")
        self.write("README.md",
                   "python tools/valid.py\npython3 tools\\valid.py\n"
                   "python tools/missing.py\npython scripts/legacy.py\n")
        errors = gate.scan(self.root)[1]
        self.assertEqual(len(errors), 2)
        self.assertIn("file assente", errors[0].reason)
        self.assertIn("deve usare tools/", errors[1].reason)

    def test_python_examples_are_compiled_without_execution(self):
        self.write("README.md", "```python\nraise RuntimeError('not executed')\n```\n"
                   "```python\nawait operation()\n```\n"
                   "```python\nif:\n```\n")
        errors = gate.scan(self.root)[1]
        self.assertEqual(len(errors), 1)
        self.assertIn("esempio Python 3 non valido", errors[0].reason)

    def test_unclosed_fence(self):
        self.write("README.md", "```python\nvalue = 1\n")
        self.assertEqual(gate.scan(self.root)[1][0].reason, "code fence non bilanciato")

    def test_exit_status(self):
        violation = gate.Violation(gate.ROOT / "README.md", "broken")
        for errors, status in (([], 0), ([violation], 1)):
            with patch.object(gate, "scan", return_value=(1, errors)):
                with patch("builtins.print"):
                    self.assertEqual(gate.main(), status)

    def test_unreadable_document_reports_a_violation(self):
        path = self.write("README.md", "")
        path.write_bytes(b"\xff")
        count, errors = gate.scan(self.root)
        self.assertEqual(count, 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("documento illeggibile", errors[0].reason)


if __name__ == "__main__":
    unittest.main()
