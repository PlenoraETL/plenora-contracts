import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_schema_immutability as immutability
import validate_specs as validator
from conformance_checks import adoption_errors, capability_errors, example_inventory_errors

ROOT = Path(__file__).resolve().parents[1]


def example(name):
    return json.loads((ROOT / "examples/valid" / name).read_text(encoding="utf-8"))


class PublicSemanticsTests(unittest.TestCase):
    def test_conflicting_operation_identity_is_rejected(self):
        document = example("capabilities-v2.json")
        duplicate = copy.deepcopy(document["operations"][0])
        duplicate.update(status="unavailable", reason="deliberate counterexample")
        document["operations"].append(duplicate)
        self.assertTrue(any("CAP-005" in error for error in capability_errors(document)))

    def test_distinct_operation_versions_remain_allowed(self):
        document = example("capabilities-v2.json")
        duplicate = copy.deepcopy(document["operations"][0])
        duplicate["version"] += 1
        document["operations"].append(duplicate)
        self.assertEqual(capability_errors(document), [])

    def test_undeclared_operation_surface_is_rejected(self):
        document = example("capabilities-v2.json")
        document["operations"][0]["surfaces"].append("runtime")
        self.assertTrue(any("CAP-007" in error for error in capability_errors(document)))

    def test_manifest_contract_cannot_have_two_adoption_statuses(self):
        document = example("adoption-manifest-v4.json")
        document["contracts"].append({"id": document["contracts"][0]["id"], "status": "not_applicable"})
        self.assertTrue(any("duplicate contract" in error for error in adoption_errors(document)))

    def test_artifact_name_must_resolve_unambiguously(self):
        document = example("adoption-manifest-v4.json")
        duplicate = copy.deepcopy(document["artifacts"][0])
        duplicate["digest"] = "sha256:" + "0" * 64
        document["artifacts"].append(duplicate)
        self.assertTrue(any("ambiguous artifact" in error for error in adoption_errors(document)))

    def test_repeated_consistent_manifest_evidence_remains_allowed(self):
        document = example("adoption-manifest-v4.json")
        for collection in ("artifacts", "contracts"):
            repeated = copy.deepcopy(document[collection][0])
            repeated["verification"] = ["another public verification command"]
            document[collection].append(repeated)
        self.assertEqual(adoption_errors(document), [])

    def test_deviation_must_reference_declared_artifact(self):
        document = example("adoption-manifest-v4.json")
        document["deviations"][0]["artifact"] = "absent"
        self.assertTrue(any("undeclared artifact" in error for error in adoption_errors(document)))

    def test_deviation_surface_must_match_named_artifact(self):
        document = example("adoption-manifest-v4.json")
        document["deviations"][0]["surface"] = "cli"
        self.assertTrue(any("surface differs" in error for error in adoption_errors(document)))

    def test_surface_only_deviation_can_describe_missing_surface(self):
        document = example("adoption-manifest-v4.json")
        document["deviations"][0].pop("artifact")
        document["deviations"][0]["surface"] = "runtime"
        self.assertEqual(adoption_errors(document), [])

    def test_retained_adoption_versions_still_conform(self):
        for version in (2, 3, 4):
            with self.subTest(version=version):
                self.assertEqual(adoption_errors(example(f"adoption-manifest-v{version}.json")), [])

    def test_published_version_grammar_does_not_silently_become_semver(self):
        schemas = {path.name: validator.load_json(path) for path in (ROOT / "schemas").glob("*.schema.json")}
        registry = validator.schema_registry(schemas)
        for schema, filename in [
            ("capabilities-v2.schema.json", "capabilities-v2.json"),
            ("cli-envelope-v2.schema.json", "cli-success.json"),
        ]:
            for version, accepted in [
                ("1.2.3", True), ("1.2.3-rc.1", True),
                ("1.2.3-rc.1+build.9", False), ("1.2.3-01", True),
                ("1.2.3+build..9", True),
            ]:
                with self.subTest(schema=schema, version=version):
                    document = example(filename)
                    document["component_version"] = version
                    self.assertEqual(not validator.instance_errors(schemas[schema], document, registry), accepted)

    def test_complete_gate_detects_semantic_corruption_of_valid_example(self):
        original = validator.load_json
        for name, change in [
            ("capabilities-v2.json", lambda doc: doc["operations"][0]["surfaces"].append("runtime")),
            ("adoption-manifest-v4.json", lambda doc: doc["deviations"][0].update(artifact="absent")),
        ]:
            def corrupted(path):
                document = original(path)
                if path == ROOT / "examples/valid" / name:
                    change(document)
                return document
            with self.subTest(name=name), patch.object(validator, "load_json", corrupted):
                with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(validator.main(), 1)


class ExampleInventoryTests(unittest.TestCase):
    def test_unregistered_negative_example_fails_complete_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "examples", root / "examples")
            (root / "examples/invalid/unregistered.json").write_text("{}", encoding="utf-8")
            with patch.object(validator, "ROOT", root), contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(validator.main(), 1)
            self.assertIn("unregistered example", output.getvalue())

    def test_missing_conflicting_and_duplicate_registrations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "examples/valid").mkdir(parents=True)
            (root / "examples/valid/probe.json").write_text("{}", encoding="utf-8")
            registrations = [
                ("examples/valid/probe.json", "invalid", "check"),
                ("examples/valid/probe.json", "valid", "check"),
                ("examples/valid/missing.json", "valid", "check"),
            ]
            errors = example_inventory_errors(root, registrations)
            for fragment in ("classification conflicts", "duplicate example", "is missing"):
                self.assertTrue(any(fragment in error for error in errors), errors)

    def test_structural_and_semantic_checks_can_share_one_example(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "examples/valid").mkdir(parents=True)
            (root / "examples/valid/probe.json").write_text("{}", encoding="utf-8")
            self.assertEqual(example_inventory_errors(root, [
                ("examples/valid/probe.json", "valid", "schema"),
                ("examples/valid/probe.json", "valid", "semantics"),
            ]), [])


class SchemaImmutabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.schema_path = self.root / "schemas/probe-v1.schema.json"
        self.schema_path.parent.mkdir()
        self.schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://schemas.plenora.dev/probe-v1.schema.json",
            "description": "annotation",
            "properties": {"description": {"const": "literal", "description": "annotation"}},
            "enum": [{"description": "literal"}],
            "$defs": {"limit": {"maxLength": 2048}},
        }
        self.write()
        for args in [
            ["init", "--quiet"], ["add", "schemas"],
            ["-c", "user.name=Contract tests", "-c", "user.email=tests@example.invalid", "commit", "--quiet", "-m", "ratified"],
        ]:
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        self.base = immutability.git(self.root, "rev-parse", "HEAD").strip()

    def write(self):
        self.schema_path.write_text(json.dumps(self.schema), encoding="utf-8")

    def test_validation_change_without_new_version_is_rejected(self):
        self.schema["$defs"]["limit"]["maxLength"] = 4096
        self.write()
        self.assertTrue(any("assertions changed" in error for error in immutability.check(self.root, self.base)))

    def test_annotation_changes_do_not_require_new_version(self):
        self.schema["description"] = "clarification"
        self.schema["properties"]["description"]["description"] = "clarification"
        self.write()
        self.assertEqual(immutability.check(self.root, self.base), [])

    def test_property_named_description_is_not_an_annotation(self):
        self.schema["properties"]["description"]["const"] = "changed"
        self.write()
        self.assertTrue(immutability.check(self.root, self.base))

    def test_description_inside_enum_literal_is_not_an_annotation(self):
        self.schema["enum"][0]["description"] = "changed"
        self.write()
        self.assertTrue(immutability.check(self.root, self.base))

    def declare_erratum(self, previous, corrected, last_base=None, section=None):
        decision = self.root / "decisions/probe.md"
        decision.parent.mkdir(exist_ok=True)
        if section is None:
            section = "## Erratum\n\n`probe-v1.schema.json` corrected before adoption.\n"
        decision.write_text("# Probe\n\n" + section, encoding="utf-8")
        return immutability.Erratum(
            immutability.assertions_digest(previous),
            immutability.assertions_digest(corrected),
            "decisions/probe.md",
            last_base or self.base,
        )

    def commit_unrelated(self):
        (self.root / "notes.txt").write_text("later", encoding="utf-8")
        for args in [
            ["add", "notes.txt"],
            ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "--quiet", "-m", "later"],
        ]:
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        return immutability.git(self.root, "rev-parse", "HEAD").strip()

    def test_erratum_requires_its_decision(self):
        relative = "schemas/probe-v1.schema.json"
        previous = json.loads(json.dumps(self.schema))
        self.schema["$defs"]["limit"]["maxLength"] = 4096
        self.write()
        corrected = json.loads(json.dumps(self.schema))
        for name, section in [
            ("missing decision", None),
            ("no erratum section", "## Context\n\n`probe-v1.schema.json`\n"),
            ("erratum names another file", "## Erratum\n\n`other-v1.schema.json`\n"),
            ("named only after the section", "## Erratum\n\nnothing\n\n## Notes\n\n`probe-v1.schema.json`\n"),
        ]:
            with self.subTest(case=name):
                erratum = self.declare_erratum(previous, corrected, section=section)
                if section is None:
                    (self.root / "decisions/probe.md").unlink()
                with unittest.mock.patch.dict(immutability.ERRATA, {relative: erratum}):
                    errors = immutability.check(self.root, self.base)
                self.assertTrue(any("erratum for" in error for error in errors), errors)
                self.assertTrue(any("assertions changed" in error for error in errors), errors)

    def test_erratum_is_bound_to_bases_that_published_the_error(self):
        relative = "schemas/probe-v1.schema.json"
        previous = json.loads(json.dumps(self.schema))
        later = self.commit_unrelated()
        self.schema["$defs"]["limit"]["maxLength"] = 4096
        self.write()
        corrected = json.loads(json.dumps(self.schema))
        erratum = self.declare_erratum(previous, corrected, last_base=later)
        with unittest.mock.patch.dict(immutability.ERRATA, {relative: erratum}):
            self.assertEqual(immutability.check(self.root, later), [])
            self.assertEqual(immutability.check(self.root, self.base), [])
        # A base after the declared last base: the erratum no longer applies.
        erratum = self.declare_erratum(previous, corrected, last_base=self.base)
        with unittest.mock.patch.dict(immutability.ERRATA, {relative: erratum}):
            self.assertEqual(immutability.check(self.root, self.base), [])
            self.assertTrue(any(
                "assertions changed" in error for error in immutability.check(self.root, later)
            ))

    def test_repository_errata_are_verifiable(self):
        for relative, erratum in immutability.ERRATA.items():
            with self.subTest(path=relative):
                self.assertEqual(immutability.erratum_errors(
                    relative, erratum, lambda path: (ROOT / path).read_text(encoding="utf-8")
                ), [])
                document = json.loads((ROOT / relative).read_text(encoding="utf-8"))
                self.assertEqual(
                    immutability.digest(immutability.comparable(relative, document)), erratum.after
                )

    def test_main_checks_the_fork_point_without_an_event_base(self):
        # The floor predates a schema that main published later: only the
        # fork point from origin/main protects it on a branch's first push.
        floor = self.base
        later_schema = self.schema_path.with_name("later-v1.schema.json")
        later_schema.write_text(json.dumps(dict(self.schema, **{"$id": "later"})), encoding="utf-8")
        for args in [
            ["add", "schemas"],
            ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "--quiet", "-m", "main"],
            ["update-ref", "refs/remotes/origin/main", "HEAD"],
        ]:
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        later_schema.write_text(json.dumps(dict(self.schema, **{"$id": "later", "maxLength": 1})), encoding="utf-8")
        with patch.object(immutability, "ROOT", self.root), patch.object(immutability, "RATIFIED_BASE", floor), \
                patch.dict("os.environ", {"PLENORA_SCHEMA_BASE": "0" * 40}), patch("sys.argv", ["check"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(immutability.main(), 1)
        self.assertIn("later-v1.schema.json", output.getvalue())

    def run_main(self, environment):
        # The run's own CI markers (this suite runs in CI too) are removed.
        environment = {
            **{key: value for key, value in os.environ.items() if key not in immutability.CI_MARKERS},
            "PLENORA_SCHEMA_BASE": "0" * 40, "PLENORA_ALLOW_NO_FORK_POINT": "", **environment,
        }
        with patch.object(immutability, "ROOT", self.root), patch.object(immutability, "RATIFIED_BASE", self.base), \
                patch.dict("os.environ", environment, clear=True), patch("sys.argv", ["check"]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            status = immutability.main()
        return status, output.getvalue()

    def test_missing_fork_point_fails_unless_waived_outside_ci(self):
        # This repository has no origin/main.
        status, output = self.run_main({})
        self.assertEqual(status, 1)
        self.assertIn("cannot find where HEAD left", output)
        status, output = self.run_main({"PLENORA_ALLOW_NO_FORK_POINT": "1"})
        self.assertEqual(status, 0, output)
        self.assertIn("note:", output)
        for marker in [{"GITHUB_ACTIONS": "true"}, {"GITHUB_ACTIONS": ""}, {"CI": "false"}, {"GITHUB_RUN_ID": "1"}]:
            with self.subTest(marker=marker):
                status, _ = self.run_main({"PLENORA_ALLOW_NO_FORK_POINT": "1", **marker})
                self.assertEqual(status, 1)
        subprocess.run(["git", "-C", str(self.root), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
        self.assertEqual(self.run_main({"GITHUB_ACTIONS": "true"})[0], 0)

    def test_only_the_declared_erratum_transition_is_allowed(self):
        relative = "schemas/probe-v1.schema.json"
        previous = json.loads(json.dumps(self.schema))
        self.schema["$defs"]["limit"]["maxLength"] = 4096
        self.write()
        corrected = json.loads(json.dumps(self.schema))
        erratum = self.declare_erratum(previous, corrected)
        with unittest.mock.patch.dict(immutability.ERRATA, {relative: erratum}):
            self.assertEqual(immutability.check(self.root, self.base), [])
            # Any other change of the same schema is still a new version.
            self.schema["$defs"]["limit"]["maxLength"] = 8192
            self.write()
            self.assertTrue(immutability.check(self.root, self.base))
        # Without the declaration the corrected schema is rejected.
        self.schema = corrected
        self.write()
        self.assertTrue(immutability.check(self.root, self.base))

    def test_removing_or_renaming_old_schema_is_rejected(self):
        self.schema_path.rename(self.schema_path.with_name("renamed.schema.json"))
        self.assertTrue(any("removed" in error for error in immutability.check(self.root, self.base)))

    def test_new_version_is_allowed_while_old_version_remains(self):
        successor = dict(self.schema, **{"$id": "https://schemas.plenora.dev/probe-v2.schema.json"})
        self.schema_path.with_name("probe-v2.schema.json").write_text(json.dumps(successor), encoding="utf-8")
        self.assertEqual(immutability.check(self.root, self.base), [])

    def test_new_file_cannot_reuse_an_existing_schema_identifier(self):
        self.schema_path.with_name("alias.schema.json").write_text(json.dumps(self.schema), encoding="utf-8")
        self.assertTrue(any("duplicate schema" in error for error in immutability.check(self.root, self.base)))

    def test_ignored_schema_is_still_checked(self):
        (self.root / ".gitignore").write_text("schemas/alias.schema.json\n", encoding="utf-8")
        self.schema_path.with_name("alias.schema.json").write_text(json.dumps(self.schema), encoding="utf-8")
        self.assertTrue(any("duplicate schema" in error for error in immutability.check(self.root, self.base)))

    def test_mutable_or_missing_baseline_fails_closed(self):
        with self.assertRaises(ValueError):
            immutability.check(self.root, "main")
        with self.assertRaises(subprocess.CalledProcessError):
            immutability.check(self.root, "f" * 40)


class PublishedDocumentImmutabilityTests(unittest.TestCase):
    """Catalogs, registries, binding maps and vectors against a base: the
    compatible additions of COMPATIBILITY.md pass, every other change fails."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        operation = {
            "id": "probe.read", "version": 1, "requirement": "required", "summary": "Read.",
            "surfaces": ["rust"],
            "input": {"contract": "probe-in-v1", "content_types": ["application/json"], "interchange_contracts": []},
            "output": {"contract": "probe-out-v1", "content_types": ["application/json"], "interchange_contracts": []},
            "side_effect": "none",
            "controls": {"cancellation": True, "deadline": True, "idempotency_key": False},
            "attributes": {"contract": "probe-attributes-v1"},
        }
        self.documents = {
            "schemas/probe-v1.schema.json": {"$id": "probe", "type": "object"},
            "catalogs/probe-tools-v1.json": {
                "contract": "plenora-public-catalog-v1", "component": "plenora-probe-tools",
                "status": "provisional",
                "target_surfaces": {"rust": "required", "cli": "not_applicable", "python_sdk": "conditional", "runtime": "undecided"},
                "operations": [operation],
            },
            "catalogs/probe-kernels-v1.json": {
                "contract": "plenora-operation-registry-v1", "registry": "probe-kernels-v1",
                "operations": [{"id": "table.a", "version": 1, "family": "table"}],
            },
            "bindings/probe-v1.json": {
                "contract": "plenora-surface-bindings-v1", "surface": "python_sdk",
                "components": [
                    {"component": "plenora-probe-tools", "artifact": "probe", "discovery": ["probe.version"],
                     "bindings": [{"operation": "probe.read", "version": 1, "requirement": "required",
                                   "entrypoints": ["probe.read", "probe.aread"]}]},
                    {"component": "plenora-other-tools", "artifact": None, "discovery": [], "bindings": []},
                ],
            },
            "vectors/runtime-v1/probe-request.json": {"kind": "request", "payload": {"rows": [1]}},
        }
        self.write_all()
        for args in [
            ["init", "--quiet"], ["add", "."],
            ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "--quiet", "-m", "published"],
        ]:
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        self.base = immutability.git(self.root, "rev-parse", "HEAD").strip()

    def write_all(self):
        for relative, document in self.documents.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(document), encoding="utf-8")

    def errors_after(self, relative, change):
        document = copy.deepcopy(self.documents[relative])
        change(document)
        (self.root / relative).write_text(json.dumps(document), encoding="utf-8")
        try:
            return immutability.check(self.root, self.base)
        finally:
            self.write_all()

    def test_unchanged_documents_pass(self):
        self.assertEqual(immutability.check(self.root, self.base), [])

    def test_compatible_additions_pass(self):
        added = copy.deepcopy(self.documents["catalogs/probe-tools-v1.json"]["operations"][0])
        added["version"] = 2
        binding = {"operation": "probe.read", "version": 2, "requirement": "required", "entrypoints": ["probe.read2"]}
        cases = {
            "catalogs/probe-tools-v1.json": [
                ("new operation identity", lambda doc: doc["operations"].append(copy.deepcopy(added))),
                ("new surface", lambda doc: doc["operations"][0]["surfaces"].append("python_sdk")),
                ("open surface selected", lambda doc: doc["target_surfaces"].update(cli="conditional", runtime="required")),
                ("summary clarified", lambda doc: doc["operations"][0].update(summary="Read one table.")),
                ("promotion to normative", lambda doc: doc.update(status="normative")),
            ],
            "catalogs/probe-kernels-v1.json": [
                ("new kernel", lambda doc: doc["operations"].append({"id": "table.b", "version": 1, "family": "table"})),
            ],
            "bindings/probe-v1.json": [
                ("new binding", lambda doc: doc["components"][0]["bindings"].append(dict(binding))),
                ("new discovery entrypoint", lambda doc: doc["components"][0]["discovery"].append("probe.capabilities")),
                ("artifact for an absent surface", lambda doc: doc["components"][1].update(artifact="other")),
            ],
        }
        for relative, changes in cases.items():
            for name, change in changes:
                with self.subTest(case=name):
                    self.assertEqual(self.errors_after(relative, change), [])
        (self.root / "vectors/runtime-v1/probe-success.json").write_text("{}", encoding="utf-8")
        self.assertEqual(immutability.check(self.root, self.base), [])

    def test_changes_to_published_identities_fail(self):
        cases = {
            "catalogs/probe-tools-v1.json": [
                ("side effect", lambda doc: doc["operations"][0].update(side_effect="remote")),
                ("input contract", lambda doc: doc["operations"][0]["input"].update(contract="probe-in-v2")),
                ("controls", lambda doc: doc["operations"][0]["controls"].update(deadline=False)),
                ("attributes", lambda doc: doc["operations"][0]["attributes"].update(extra=True)),
                ("requirement", lambda doc: doc["operations"][0].update(requirement="conditional")),
                ("dropped surface", lambda doc: doc["operations"][0]["surfaces"].clear()),
                ("removed operation", lambda doc: doc["operations"].clear()),
                ("repeated identity", lambda doc: doc["operations"].append(copy.deepcopy(doc["operations"][0]))),
                ("selected surface changed", lambda doc: doc["target_surfaces"].update(rust="conditional")),
                ("status demoted", lambda doc: doc.update(status="retired")),
                ("component", lambda doc: doc.update(component="plenora-renamed-tools")),
            ],
            "catalogs/probe-kernels-v1.json": [
                ("kernel version", lambda doc: doc["operations"][0].update(version=2)),
                ("kernel removed", lambda doc: doc["operations"].clear()),
                ("registry identifier", lambda doc: doc.update(registry="probe-kernels-v9")),
            ],
            "bindings/probe-v1.json": [
                ("entrypoint renamed", lambda doc: doc["components"][0]["bindings"][0].update(entrypoints=["probe.load"])),
                ("requirement", lambda doc: doc["components"][0]["bindings"][0].update(requirement="conditional")),
                ("binding removed", lambda doc: doc["components"][0]["bindings"].clear()),
                ("artifact changed", lambda doc: doc["components"][0].update(artifact="renamed")),
                ("discovery dropped", lambda doc: doc["components"][0]["discovery"].clear()),
                ("section removed", lambda doc: doc["components"].pop()),
                ("surface", lambda doc: doc.update(surface="cli")),
            ],
            "vectors/runtime-v1/probe-request.json": [
                ("payload", lambda doc: doc["payload"]["rows"].append(2)),
            ],
        }
        for relative, changes in cases.items():
            for name, change in changes:
                with self.subTest(path=relative, case=name):
                    errors = self.errors_after(relative, change)
                    self.assertTrue(any(relative in error for error in errors), errors)

    def test_removed_documents_fail(self):
        for relative in self.documents:
            if relative.startswith("schemas/"):
                continue
            with self.subTest(path=relative):
                (self.root / relative).unlink()
                try:
                    errors = immutability.check(self.root, self.base)
                finally:
                    self.write_all()
                self.assertIn(f"published document removed: {relative}", errors)

    def test_case_only_rename_is_a_removal(self):
        # On a case-insensitive file system the old spelling still opens.
        relative = "vectors/runtime-v1/probe-request.json"
        renamed = "vectors/runtime-v1/PROBE-REQUEST.json"
        subprocess.run(["git", "-C", str(self.root), "mv", relative, renamed], check=True, capture_output=True)
        self.assertIn(f"published document removed: {relative}", immutability.check(self.root, self.base))

    def test_case_only_rename_outside_the_index_is_a_removal(self):
        # Renamed on disk only: the index keeps the old spelling, which a
        # case-insensitive file system still opens.
        relative = "vectors/runtime-v1/probe-request.json"
        os.rename(self.root / relative, self.root / "vectors/runtime-v1/PROBE-REQUEST.json")
        self.assertIn(f"published document removed: {relative}", immutability.check(self.root, self.base))

    def test_deleted_tracked_file_is_a_removal(self):
        relative = "catalogs/probe-kernels-v1.json"
        (self.root / relative).unlink()
        self.assertIn(f"published document removed: {relative}", immutability.check(self.root, self.base))

    def test_repeated_key_cannot_hide_a_change(self):
        path = self.root / "catalogs/probe-tools-v1.json"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace('"side_effect": "none"', '"side_effect": "remote", "side_effect": "none"'),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "repeats a JSON object key"):
            immutability.check(self.root, self.base)

    def test_unrecognized_catalog_document_is_compared_whole(self):
        relative = "catalogs/probe-tools-v1.json"
        self.documents[relative]["contract"] = "plenora-public-catalog-v9"
        self.write_all()
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
             "commit", "--quiet", "-am", "unknown"], check=True, capture_output=True,
        )
        self.base = immutability.git(self.root, "rev-parse", "HEAD").strip()
        errors = self.errors_after(relative, lambda doc: doc["operations"][0]["surfaces"].append("cli"))
        self.assertTrue(any("document changed" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
