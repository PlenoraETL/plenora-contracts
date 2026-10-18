"""Public Catalogs 2.0 CAT-003 (decision 0015): the surfaces a profile
declares intentionally absent stay absent in every catalog of contract
version 2, and the profile states the rule that gives the reason. Catalogs
of version 1 keep Public Catalogs 1.0, which has no such rule."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_specs as validator

DATABASE = validator.DATABASE_COMPONENT
PROFILE_V2 = "plenora-database-tools-profile-v2"
REASONS = (
    "**DB-ABS-001** — Transactions are not bound to the CLI or the runtime.\n\n"
    "**DB-ABS-002** — The statement could run twice on the runtime.\n"
)
ABSENCES = {
    (DATABASE, "database.transaction.commit", 1): ({"cli", "runtime"}, "DB-ABS-001"),
    (DATABASE, "database.execute", 1): ({"runtime"}, "DB-ABS-002"),
}


def versions(with_v2=True):
    """Every catalog version on disk and, unless told otherwise, a database
    catalog of contract version 2 next to them: the rules of this test do
    not depend on which catalogs a later change publishes."""
    by_version = copy.deepcopy(validator.catalog_versions(validator.load_catalogs()))
    if with_v2 and not any(
        catalog["contract"] == validator.CATALOG_V2 for catalog in by_version[DATABASE].values()
    ):
        catalog = copy.deepcopy(by_version[DATABASE][max(by_version[DATABASE])])
        catalog.update(contract=validator.CATALOG_V2, profile=PROFILE_V2)
        by_version[DATABASE][max(by_version[DATABASE]) + 1] = catalog
    return by_version


def latest_v2(by_version, component):
    return max(
        version for version, catalog in by_version[component].items()
        if catalog["contract"] == validator.CATALOG_V2
    )


def operation(catalog, identifier, version):
    for item in catalog["operations"]:
        if (item["id"], item["version"]) == (identifier, version):
            return item
    raise AssertionError((identifier, version))


class Profiles:
    """`profile_path` sends the version 2 database profile to a file with
    the given bytes; every other profile stays on disk."""

    def __init__(self, content):
        self.content = content
        self.original = validator.profile_path

    def __call__(self, component, profile):
        path = self.original(component, profile)
        if component != DATABASE or profile != PROFILE_V2 or self.content is None:
            return path
        target = Path(tempfile.mkdtemp()) / "database-tools-v2.md"
        target.write_bytes(self.content)
        return target

    def __enter__(self):
        self.patch = patch.object(validator, "profile_path", self)
        self.patch.start()
        return self

    def __exit__(self, *exc):
        self.patch.stop()


def stated(text=REASONS):
    return f"Profile identifier: `{PROFILE_V2}`\n\n{text}".encode("utf-8")


class IntentionalAbsenceTests(unittest.TestCase):
    def setUp(self):
        self.table = patch.dict(validator.INTENTIONAL_ABSENCES, ABSENCES, clear=True)
        self.table.start()
        self.addCleanup(self.table.stop)

    def errors(self, by_version, content=None):
        with Profiles(stated() if content is None else content):
            return validator.intentional_absence_errors(by_version)

    def test_published_catalogs_respect_every_absence(self):
        with patch.dict(validator.INTENTIONAL_ABSENCES, clear=True):
            self.assertEqual(validator.intentional_absence_errors(versions(with_v2=False)), [])
        self.assertEqual(self.errors(versions()), [])

    def test_only_catalogs_of_contract_version_2(self):
        """A catalog of version 1 keeps Public Catalogs 1.0: its surfaces are
        not checked against CAT-003, and its profile states no absence."""
        by_version = versions()
        for version, catalog in by_version[DATABASE].items():
            if catalog["contract"] != validator.CATALOG_V2:
                operation(catalog, "database.execute", 1)["surfaces"].append("runtime")
        self.assertEqual(self.errors(by_version), [])
        operation(by_version[DATABASE][latest_v2(by_version, DATABASE)], "database.execute", 1)[
            "surfaces"
        ].append("runtime")
        errors = self.errors(by_version)
        self.assertEqual(len(errors), 1)
        self.assertIn("DB-ABS-002", errors[0])

    def test_a_transaction_on_the_runtime_is_rejected(self):
        by_version = versions()
        operation(by_version[DATABASE][latest_v2(by_version, DATABASE)], "database.transaction.commit", 1)[
            "surfaces"
        ].append("runtime")
        errors = self.errors(by_version)
        self.assertEqual(len(errors), 1)
        self.assertIn("DB-ABS-001", errors[0])

    def test_the_profile_must_state_the_rule(self):
        errors = self.errors(versions(), stated("Nothing declared here.\n"))
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("does not state" in error for error in errors))

    def test_the_file_is_read_as_written(self):
        """CAT-003: the reading keeps the terminators, so a CR alone fails in
        the file as it fails in the text; a BOM and invalid UTF-8 fail too."""
        for name, content in {
            "isolated CR": stated("**DB-ABS-001** — a reason.\r\rnext\n**DB-ABS-002** — a reason.\n"),
            "BOM": "﻿".encode("utf-8") + stated(),
            "not UTF-8": stated() + b"\xe2\x80\n",
        }.items():
            errors = self.errors(versions(), content)
            with self.subTest(name):
                self.assertTrue(errors)
                self.assertTrue(all("(CAT-003)" in error for error in errors), errors)
                # One failure per catalog version, never one per rule.
                self.assertEqual(len(errors), 1)
        crlf = stated().replace(b"\n", b"\r\n")
        self.assertEqual(self.errors(versions(), crlf), [])

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
        self.assertTrue(validator.reason_is_stated("**DB-ABS-002** — a reason.", "DB-ABS-002"))
        self.assertFalse(validator.reason_is_stated("**DB-ABS-002** — a reason .", "DB-ABS-002"))
        self.assertFalse(validator.reason_is_stated("**DB-ABS-002** — a reason　.", "DB-ABS-002"))
        refused = {
            "isolated CR": "**DB-ABS-002** — a reason.\r\rnext without period",
            "CR at the end": "**DB-ABS-002** — a reason.\r",
            "CR elsewhere in the profile": "intro\rmore\n**DB-ABS-002** — a reason.",
            "BOM at the start": "﻿**DB-ABS-002** — a reason.",
            "BOM inside": "**DB-ABS-002** — a﻿ reason.",
            "BOM-only line": "**DB-ABS-002** — a reason.\n﻿\nnext without period",
            "NBSP-only line": "**DB-ABS-002** — a reason.\n \nnext without period",
            "ideographic space line": "**DB-ABS-002** — a reason.\n　 \t\nnext without period",
            "vertical tab": "**DB-ABS-002** — a reason.\x0b",
            "form feed": "**DB-ABS-002** — a reason.\x0c",
            "next line": "**DB-ABS-002** — a reason.\x85next",
            "line separator": "**DB-ABS-002** — a reason. next",
            "paragraph separator": "**DB-ABS-002** — a reason. next",
        }
        for name, text in refused.items():
            with self.subTest(name), self.assertRaises(validator.ProfileTextError):
                validator.reason_is_stated(text, "DB-ABS-002")
        self.assertEqual(validator.stated_reason("**DB-ABS-002** — \n\nnext", "DB-ABS-002"), "")
        self.assertEqual(validator.stated_reason("nothing", "DB-ABS-002"), "")
        errors = self.errors(versions(), stated("**DB-ABS-001** — no period\n\n**DB-ABS-002** —\n"))
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("without a reason" in error for error in errors))

    def test_an_absence_for_an_unknown_operation_is_reported(self):
        key = (validator.DATA_COMPONENT, "data.unknown", 1)
        with patch.dict(validator.INTENTIONAL_ABSENCES, {key: ({"cli"}, "DT-ABS-001")}):
            errors = self.errors(versions())
        self.assertEqual(errors, [f"declared absence for unknown operation {key}"])

    def test_an_absence_named_only_by_a_catalog_of_version_1_is_unknown(self):
        """The operation must be listed by a catalog of version 2: a catalog of
        version 1 is outside CAT-003, so it cannot satisfy the declaration."""
        by_version = {
            component: {
                version: catalog for version, catalog in catalogs.items()
                if catalog["contract"] != validator.CATALOG_V2
            }
            for component, catalogs in versions(with_v2=False).items()
        }
        errors = self.errors(by_version)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all(error.startswith("declared absence for unknown operation") for error in errors))


class PublishedAbsenceTests(unittest.TestCase):
    """The absences the profiles of version 2 declare (decision 0015), on the
    catalogs as published."""

    EXPECTED = {
        (DATABASE, "database.transaction.begin", 1): ({"cli", "runtime"}, "DB-ABS-001"),
        (DATABASE, "database.transaction.commit", 1): ({"cli", "runtime"}, "DB-ABS-001"),
        (DATABASE, "database.transaction.rollback", 1): ({"cli", "runtime"}, "DB-ABS-001"),
        (DATABASE, "database.transaction.savepoint", 1): ({"cli", "runtime"}, "DB-ABS-001"),
        (DATABASE, "database.execute", 1): ({"runtime"}, "DB-ABS-002"),
        (validator.DATA_COMPONENT, "data.run", 3): ({"cli", "python_sdk"}, "DT-ABS-001"),
        (validator.DATA_COMPONENT, "data.run", 2): ({"runtime"}, "DT-ABS-002"),
    }

    def test_the_declared_absences(self):
        self.assertEqual(validator.INTENTIONAL_ABSENCES, self.EXPECTED)
        self.assertEqual(validator.intentional_absence_errors(versions(with_v2=False)), [])

    def test_the_current_catalogs_are_of_version_2(self):
        catalogs = validator.load_catalogs()
        for component in (DATABASE, validator.DATA_COMPONENT, "plenora-io-tools"):
            with self.subTest(component):
                self.assertEqual(catalogs[component]["contract"], validator.CATALOG_V2)

    def test_adding_an_absent_surface_is_refused(self):
        for (component, identifier, version), (absent, rule) in self.EXPECTED.items():
            for surface in sorted(absent):
                by_version = versions(with_v2=False)
                operation(by_version[component][latest_v2(by_version, component)], identifier, version)[
                    "surfaces"
                ].append(surface)
                with self.subTest(identifier=identifier, surface=surface):
                    errors = validator.intentional_absence_errors(by_version)
                    self.assertEqual(len(errors), 1)
                    self.assertIn(rule, errors[0])

    def test_the_catalog_gate_runs_the_check(self):
        catalogs = copy.deepcopy(validator.load_catalogs())
        operation(catalogs[DATABASE], "database.execute", 1)["surfaces"].append("runtime")
        errors = validator.validate_catalog_semantics(catalogs)
        self.assertTrue(any("DB-ABS-002" in error for error in errors), errors)


class CatalogVersionTests(unittest.TestCase):
    def test_each_catalog_is_validated_against_the_schema_of_its_contract(self):
        self.assertEqual(validator.catalog_schema_name({"contract": validator.CATALOG_V2}),
                         "public-catalog-v2.schema.json")
        self.assertEqual(validator.catalog_schema_name({"contract": "plenora-public-catalog-v1"}),
                         "public-catalog-v1.schema.json")
        # An unknown contract is validated against version 1, whose `const`
        # refuses it: never silently accepted.
        self.assertEqual(validator.catalog_schema_name({"contract": "plenora-public-catalog-v9"}),
                         "public-catalog-v1.schema.json")
        schemas = {name: validator.load_json(validator.ROOT / "schemas" / name)
                   for name in validator.EXPECTED_SCHEMAS}
        registry = validator.schema_registry(schemas)
        catalog = copy.deepcopy(validator.load_catalogs()[DATABASE])
        catalog.update(contract=validator.CATALOG_V2, profile=PROFILE_V2)
        self.assertEqual(validator.instance_errors(schemas["public-catalog-v2.schema.json"], catalog, registry), [])
        self.assertNotEqual(validator.instance_errors(schemas["public-catalog-v1.schema.json"], catalog, registry), [])
        original = validator.load_json

        def as_v2(path):
            document = original(path)
            if Path(path).parent.name == "catalogs" and Path(path).name == "database-tools-v1.json":
                document = copy.deepcopy(document)
                document.update(contract=validator.CATALOG_V2, profile=PROFILE_V2)
            return document

        with patch.object(validator, "load_json", as_v2):
            self.assertEqual(validator.validate_machine_documents(schemas, registry), [])

    def test_the_vectors_of_runtime_binding_2_are_checked(self):
        """vectors/runtime-v2 goes through the schema and the semantic checks
        of vectors/runtime-v1 (Runtime Binding 2.0 section 10)."""
        paths = validator.runtime_vector_paths()
        self.assertTrue(any(path.parent.name == "runtime-v2" for path in paths))
        self.assertTrue(any(path.parent.name == "runtime-v1" for path in paths))
        original = validator.load_json

        def broken(path):
            document = original(path)
            if Path(path).parent.name == "runtime-v2":
                document = copy.deepcopy(document)
                document["metadata"]["plenora.operation.version"] = "9"
            return document

        catalogs = validator.load_catalogs()
        schemas = {name: validator.load_json(validator.ROOT / "schemas" / name)
                   for name in validator.EXPECTED_SCHEMAS}
        registry = validator.schema_registry(schemas)
        self.assertEqual(validator.validate_runtime_vectors(catalogs, schemas, registry), [])
        with patch.object(validator, "load_json", broken):
            errors = validator.validate_runtime_vectors(catalogs, schemas, registry)
        self.assertTrue(any("runtime-v2" in error for error in errors), errors)


class ImmutabilityTests(unittest.TestCase):
    def test_a_catalog_of_version_2_follows_the_catalog_rules(self):
        """COMPATIBILITY.md: a published catalog may add a surface and never
        remove one, whatever its contract version."""
        import check_schema_immutability as guard

        catalog = copy.deepcopy(validator.load_catalogs()[DATABASE])
        catalog.update(contract=validator.CATALOG_V2, profile=PROFILE_V2)
        position, narrow = next(
            (position, item) for position, item in enumerate(catalog["operations"]) if len(item["surfaces"]) < 4
        )
        missing = sorted({"rust", "cli", "python_sdk", "runtime"} - set(narrow["surfaces"]))[0]
        grown = copy.deepcopy(catalog)
        grown["operations"][position]["surfaces"].append(missing)
        shrunk = copy.deepcopy(catalog)
        shrunk["operations"][position]["surfaces"].pop()
        path = "catalogs/database-tools-v2.json"
        self.assertEqual(guard.document_changes(path, catalog, grown), [])
        self.assertNotEqual(guard.document_changes(path, catalog, shrunk), [])


if __name__ == "__main__":
    unittest.main()
