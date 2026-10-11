"""Public Catalogs 1.0 CAT-003 (decision 0015): the surfaces a profile
declares intentionally absent stay absent in every catalog version, and the
profile states the rule that gives the reason."""

import copy
import tempfile
import unittest
from pathlib import Path

import validate_specs as validator


def versions():
    return copy.deepcopy(validator.catalog_versions(validator.load_catalogs()))


def operation(by_version, component, identifier, version):
    for catalog in by_version[component].values():
        for item in catalog["operations"]:
            if (item["id"], item["version"]) == (identifier, version):
                return item
    raise AssertionError((component, identifier, version))


class IntentionalAbsenceTests(unittest.TestCase):
    def test_published_catalogs_respect_every_absence(self):
        self.assertEqual(validator.intentional_absence_errors(versions()), [])

    def test_a_transaction_on_the_runtime_is_rejected(self):
        by_version = versions()
        operation(by_version, validator.DATABASE_COMPONENT, "database.transaction.commit", 1)[
            "surfaces"
        ].append("runtime")
        errors = validator.intentional_absence_errors(by_version)
        self.assertEqual(len(errors), 1)
        self.assertIn("DB-ABS-001", errors[0])

    def test_execute_on_the_runtime_is_rejected(self):
        by_version = versions()
        operation(by_version, validator.DATABASE_COMPONENT, "database.execute", 1)[
            "surfaces"
        ].append("runtime")
        self.assertIn("DB-ABS-002", validator.intentional_absence_errors(by_version)[0])

    def test_data_run_versions_keep_their_surfaces(self):
        by_version = versions()
        operation(by_version, validator.DATA_COMPONENT, "data.run", 3)["surfaces"].append("cli")
        operation(by_version, validator.DATA_COMPONENT, "data.run", 2)["surfaces"].append("runtime")
        errors = validator.intentional_absence_errors(by_version)
        self.assertEqual(len(errors), 2)

    def test_the_profile_must_state_the_rule(self):
        original = validator.profile_path

        def without_rules(component, profile):
            path = original(component, profile)
            if component == validator.DATABASE_COMPONENT:
                return path.with_name("missing-profile.md")
            return path

        validator.profile_path = without_rules
        try:
            errors = validator.intentional_absence_errors(versions())
        finally:
            validator.profile_path = original
        self.assertEqual(len(errors), 5)
        self.assertTrue(all("does not state" in error for error in errors))

    def test_the_file_is_read_as_written(self):
        """CAT-003: the reading keeps the terminators, so a CR alone fails in
        the file as it fails in the text; a BOM and invalid UTF-8 fail too."""
        original = validator.profile_path
        for name, content in {
            "isolated CR": "**DB-ABS-001** — a reason.\r\rnext\n**DB-ABS-002** — a reason.\n".encode("utf-8"),
            "BOM": "\ufeff**DB-ABS-001** — a reason.\n\n**DB-ABS-002** — a reason.\n".encode("utf-8"),
            "not UTF-8": b"**DB-ABS-001** \xe2\x80 a reason.\n",
        }.items():
            def written(component, profile, content=content):
                path = original(component, profile)
                if component != validator.DATABASE_COMPONENT:
                    return path
                target = Path(tempfile.mkdtemp()) / "database-tools.md"
                target.write_bytes(f"Profile identifier: `{profile}`\n\n".encode("utf-8") + content)
                return target

            validator.profile_path = written
            try:
                errors = validator.intentional_absence_errors(versions())
            finally:
                validator.profile_path = original
            with self.subTest(name):
                self.assertTrue(errors)
                self.assertTrue(all("(CAT-003)" in error for error in errors), errors)
                # One failure per catalog version, never one per rule.
                self.assertEqual(len(errors), len(errors and set(errors)))
        crlf = "**DB-ABS-001** — a reason.\r\n\r\n**DB-ABS-002** — a reason.\r\n".encode("utf-8")

        def windows(component, profile):
            path = original(component, profile)
            if component != validator.DATABASE_COMPONENT:
                return path
            target = Path(tempfile.mkdtemp()) / "database-tools.md"
            target.write_bytes(f"Profile identifier: `{profile}`\r\n\r\n".encode("utf-8") + crlf)
            return target

        validator.profile_path = windows
        try:
            self.assertEqual(validator.intentional_absence_errors(versions()), [])
        finally:
            validator.profile_path = original

    def test_the_rule_needs_a_reason(self):
        cases = {
            "x **DB-ABS-002** — a reason.": True,
            "**DB-ABS-002** — a reason.\nsecond line.": True,
            "**DB-ABS-002** — a reason.\n\nnext paragraph without period": True,
            "**DB-ABS-002** — no period": False,
            "**DB-ABS-002** — ..": False,
            "**DB-ABS-002** — a reason..": False,
            "**DB-ABS-002** — a reason .": False,
            "**DB-ABS-002** — 12.": False,
            "**DB-ABS-002** — .": False,
            "**DB-ABS-002** —": False,
            "**DB-ABS-002** - a reason.": False,
            "**DB-ABS-002**— a reason.": False,
            "nothing": False,
            "**DB-ABS-002** — a reason.\n   \nnext without period": True,
            "**DB-ABS-002** — no period\n \t \na reason.": False,
            "**DB-ABS-002** — a reason.\r\n\r\nnext without period": True,
            "**DB-ABS-002** — a reason\r\nends here.": True,
            "**DB-ABS-002** — a reason.\n\t\n": True,
        }
        for text, expected in cases.items():
            with self.subTest(text):
                self.assertEqual(validator.reason_is_stated(text, "DB-ABS-002"), expected)
        # CAT-003: other white space is not a blank line, and a line made
        # only of it is refused; inside the text it is an ordinary character.
        self.assertTrue(validator.reason_is_stated("**DB-ABS-002** — a\u00a0reason.", "DB-ABS-002"))
        self.assertFalse(validator.reason_is_stated("**DB-ABS-002** — a reason\u00a0.", "DB-ABS-002"))
        self.assertFalse(validator.reason_is_stated("**DB-ABS-002** — a reason\u3000.", "DB-ABS-002"))
        refused = {
            "isolated CR": "**DB-ABS-002** — a reason.\r\rnext without period",
            "CR at the end": "**DB-ABS-002** — a reason.\r",
            "CR elsewhere in the profile": "intro\rmore\n**DB-ABS-002** — a reason.",
            "BOM at the start": "\ufeff**DB-ABS-002** — a reason.",
            "BOM inside": "**DB-ABS-002** — a\ufeff reason.",
            "BOM-only line": "**DB-ABS-002** — a reason.\n\ufeff\nnext without period",
            "NBSP-only line": "**DB-ABS-002** — a reason.\n\u00a0\nnext without period",
            "ideographic space line": "**DB-ABS-002** — a reason.\n\u3000 \t\nnext without period",
            "vertical tab": "**DB-ABS-002** — a reason.\x0b",
            "form feed": "**DB-ABS-002** — a reason.\x0c",
            "next line": "**DB-ABS-002** — a reason.\x85next",
            "line separator": "**DB-ABS-002** — a reason.\u2028next",
            "paragraph separator": "**DB-ABS-002** — a reason.\u2029next",
        }
        for name, text in refused.items():
            with self.subTest(name), self.assertRaises(validator.ProfileTextError):
                validator.reason_is_stated(text, "DB-ABS-002")
        self.assertEqual(validator.stated_reason("**DB-ABS-002** — \n\nnext", "DB-ABS-002"), "")
        self.assertEqual(validator.stated_reason("nothing", "DB-ABS-002"), "")
        original = validator.profile_path

        def bare(component, profile):
            path = original(component, profile)
            if component != validator.DATABASE_COMPONENT:
                return path
            target = Path(tempfile.mkdtemp()) / "database-tools.md"
            target.write_text(
                f"Profile identifier: `{profile}`\n\n**DB-ABS-001** — no period\n\n**DB-ABS-002** —\n",
                encoding="utf-8",
            )
            return target

        validator.profile_path = bare
        try:
            errors = validator.intentional_absence_errors(versions())
        finally:
            validator.profile_path = original
        self.assertEqual(len(errors), 5)
        self.assertTrue(all("without a reason" in error for error in errors))

    def test_an_absence_for_an_unknown_operation_is_reported(self):
        key = (validator.DATA_COMPONENT, "data.unknown", 1)
        validator.INTENTIONAL_ABSENCES[key] = ({"cli"}, "DT-ABS-001")
        try:
            errors = validator.intentional_absence_errors(versions())
        finally:
            del validator.INTENTIONAL_ABSENCES[key]
        self.assertEqual(errors, [f"declared absence for unknown operation {key}"])

    def test_the_catalog_gate_runs_the_check(self):
        catalogs = validator.load_catalogs()
        catalogs = copy.deepcopy(catalogs)
        for item in catalogs[validator.DATABASE_COMPONENT]["operations"]:
            if item["id"] == "database.execute":
                item["surfaces"].append("runtime")
        errors = validator.validate_catalog_semantics(catalogs)
        self.assertTrue(any("DB-ABS-002" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
