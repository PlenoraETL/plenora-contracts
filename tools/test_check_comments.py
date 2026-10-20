"""Counterexamples for comment extraction, rules and repository boundaries."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_comments as gate


class CommentGateTests(unittest.TestCase):
    def check(self, source, name="sample.py"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / name
            path.write_text(source, encoding="utf-8")
            return gate.check_file(path, root)

    def test_debt_markers_are_words(self):
        for marker in ("TODO", "FIXME", "HACK", "XXX"):
            with self.subTest(marker=marker):
                errors = self.check(f"# {marker}: repair\n")
                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0].rule, "debito anonimo")
                self.assertEqual(errors[0].line, 1)
        self.assertEqual(self.check("# METODO_CHIUSO PREFIXME_NO XXXL\n"), [])

    def test_process_history_is_rejected(self):
        for phrase in ("tranche 2", "writer pre-fix", "prima mancava", "post-review"):
            with self.subTest(phrase=phrase):
                errors = self.check(f"# {phrase}\n")
                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0].rule, "cronaca obsoleta")

    def test_current_reasons_invariants_and_compatibility_are_allowed(self):
        self.assertEqual(self.check(
            "# Reject null because the public schema requires a value.\n"
            "# Preserve compatibility with Python 3.10.\n"
            "# The digest identifies the published contract.\n"
        ), [])

    def test_python_docstrings_but_not_ordinary_strings(self):
        source = (
            '"""TODO: module"""\n'
            'value = "FIXME"\n'
            'class Example:\n'
            '    """HACK: class"""\n'
            '    def method(self):\n'
            '        """XXX: method"""\n'
            'async def task():\n'
            '    """TODO: task"""\n'
        )
        self.assertEqual([v.line for v in self.check(source)], [1, 4, 8, 6])

    def test_c_like_comments_ignore_strings_and_rust_raw_strings(self):
        source = (
            'let value = "TODO // FIXME";\n'
            'let raw = r##"XXX /* HACK */"##;\n'
            '// TODO: repair\n'
            '/* outer\n /* nested */ FIXME */\n'
        )
        errors = self.check(source, "sample.rs")
        self.assertEqual([v.line for v in errors], [3, 4])
        self.assertEqual([v.excerpt for v in errors], ["TODO", "FIXME"])

    def test_hash_and_sql_comments_ignore_quoted_markers(self):
        for name, source in (
            ("sample.yml", 'value: "# TODO" # FIXME\n'),
            ("sample.sh", 'echo "# TODO" # FIXME\n'),
            ("Dockerfile", 'RUN echo "# TODO" # FIXME\n'),
            ("sample.sql", "SELECT '-- TODO'; -- FIXME\n"),
        ):
            with self.subTest(name=name):
                self.assertEqual([v.excerpt for v in self.check(source, name)], ["FIXME"])
        self.assertEqual(self.check('{"description": "TODO"}', "sample.json"), [])

    def test_scope_includes_untracked_sources_and_excludes_contract_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            included = ["tools/a.py", "examples/b.sh", "templates/c.yml",
                        ".github/workflows/ci.yaml"]
            excluded = [f"{name}/bad.py" for name in gate.IMMUTABLE_DIRECTORIES]
            excluded += ["specs/bad.py", ".github/bad.py", "root.py",
                         "tools/__pycache__/bad.py", "tools/vendor/bad.py",
                         "examples/data.json"]
            for name in included + excluded:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# TODO\n", encoding="utf-8")
            count, errors = gate.check_repository(root)
            self.assertEqual(count, len(included))
            self.assertEqual({v.path.as_posix() for v in errors}, set(included))

    def test_exit_status(self):
        violation = gate.Violation(Path("tools/a.py"), 1, "rule", "text")
        for errors, status in (([], 0), ([violation], 1)):
            with patch.object(gate, "check_repository", return_value=(1, errors)):
                with patch("builtins.print"):
                    self.assertEqual(gate.main(), status)


if __name__ == "__main__":
    unittest.main()
