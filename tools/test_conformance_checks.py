import contextlib
import copy
import io
import json
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

    def test_mutable_or_missing_baseline_fails_closed(self):
        with self.assertRaises(ValueError):
            immutability.check(self.root, "main")
        with self.assertRaises(subprocess.CalledProcessError):
            immutability.check(self.root, "f" * 40)


if __name__ == "__main__":
    unittest.main()
