"""Regression probes for data-tools version 2: catalog versions, kernel
registries, the data plan format and the Python binding.

Each test breaks one document in memory and expects the gate to notice:
without them a check could be deleted or inverted and the suite stay green.
The integration tests go through `main()`, so a check disconnected from the
gate fails them too.
"""

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import validate_specs as validator


def gate_fails(**patches) -> bool:
    """Run the whole gate with some loaders replaced; True if it fails."""
    with contextlib.ExitStack() as stack:
        for name, replacement in patches.items():
            stack.enter_context(patch.object(validator, name, replacement))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        return validator.main() != 0


class DataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = validator.load_catalogs()
        cls.data = cls.catalogs[validator.DATA_COMPONENT]
        cls.versions = validator.load_catalog_versions()
        cls.registries = validator.data_registries()
        cls.kernel_ids = {item["id"] for item in cls.registries[max(cls.registries)]["operations"]}

    def operation(self, catalog, operation_id):
        return next(item for item in catalog["operations"] if item["id"] == operation_id)

    def mutated_versions(self, version, mutate):
        original = validator.load_catalog_versions

        def loader():
            versions = copy.deepcopy(original())
            mutate(versions[validator.DATA_COMPONENT][version])
            return versions

        return loader

    # -- helper level ----------------------------------------------------

    def test_current_target_is_version_2_and_conforms(self):
        self.assertEqual(self.data["profile"], "plenora-data-tools-profile-v2")
        self.assertEqual(validator.data_catalog_errors(self.data, 2), [])
        self.assertEqual(validator.data_catalog_errors(self.versions[validator.DATA_COMPONENT][1], 1), [])
        self.assertEqual(validator.data_registry_errors(), [])
        self.assertEqual(validator.validate_catalog_semantics(self.catalogs), [])
        self.assertEqual(validator.validate_bindings(self.catalogs), [])

    def test_version_1_stays_available_with_its_profile(self):
        versions = self.versions[validator.DATA_COMPONENT]
        self.assertEqual(sorted(versions), [1, 2])
        self.assertEqual(versions[1]["profile"], "plenora-data-tools-profile-v1")
        self.assertEqual(validator.profile_path(validator.DATA_COMPONENT, "plenora-data-tools-profile-v1").name, "data-tools.md")
        self.assertEqual(validator.profile_path(validator.DATA_COMPONENT, "plenora-data-tools-profile-v2").name, "data-tools-v2.md")

    def test_version_2_expectations(self):
        cases = {
            "run without local": lambda c: self.operation(c, "data.run").update(side_effect="none"),
            "run on runtime": lambda c: self.operation(c, "data.run")["surfaces"].append("runtime"),
            "validate on another registry": lambda c: self.operation(c, "data.validate")["attributes"].update(kernel_registry="plenora-data-kernel-catalog-v1"),
            "catalog result is the registry": lambda c: self.operation(c, "data.catalog")["output"].update(contract="plenora-data-kernel-catalog-v2"),
            "run without plan contract": lambda c: self.operation(c, "data.run")["attributes"].pop("plan_contract"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                catalog = copy.deepcopy(self.data)
                mutate(catalog)
                self.assertTrue(validator.data_catalog_errors(catalog, 2))

    def test_version_1_expectations(self):
        catalog = copy.deepcopy(self.versions[validator.DATA_COMPONENT][1])
        self.operation(catalog, "data.catalog")["output"]["contract"] = "plenora-data-kernel-catalog-v9"
        self.assertTrue(validator.data_catalog_errors(catalog, 1))

    def test_plan_names_kernels_and_numbers_are_checked(self):
        base = validator.load_json(validator.ROOT / "examples/valid/data-plan-v1.json")
        self.assertEqual(validator.data_plan_errors(base, self.kernel_ids), [])
        for mutate in (
            lambda d: d["outputs"].append("nowhere"),
            lambda d: d["steps"][0].update(op="table.filter_rows"),
            lambda d: d["inputs"].append("orders"),
        ):
            broken = copy.deepcopy(base)
            mutate(broken)
            self.assertTrue(validator.data_plan_errors(broken, self.kernel_ids))
        self.assertEqual(validator.data_plan_number_errors('{"a": 0.1, "b": 1e3, "c": 18446744073709551615}'), [])
        self.assertTrue(validator.data_plan_number_errors('{"a": 2.0000000000000000001}'))
        self.assertTrue(validator.data_plan_number_errors('{"a": 18446744073709551616}'))
        self.assertTrue(validator.data_plan_number_errors('{"a": 1e400}'))

    def test_python_binding_needs_both_api_modes(self):
        document = validator.load_json(validator.ROOT / "bindings/python-sdk-v1.json")
        self.assertEqual(validator.data_python_errors(document), [])
        section = next(item for item in document["components"] if item["component"] == validator.DATA_COMPONENT)
        section["artifact"] = None
        section["bindings"][0]["entrypoints"] = ["plenora_data.wrong"]
        self.assertTrue(validator.data_python_errors(document))

    def test_registry_versions_must_keep_identities(self):
        original = validator.data_registries

        def renamed():
            registries = copy.deepcopy(original())
            registries[max(registries)]["operations"][0]["id"] = "table.renamed"
            return registries

        with patch.object(validator, "data_registries", renamed):
            self.assertTrue(validator.data_registry_errors())

    # -- whole gate ------------------------------------------------------

    def test_gate_passes_unchanged(self):
        self.assertFalse(gate_fails())

    def test_gate_rejects_a_broken_version_1_catalog(self):
        def mutate(catalog):
            self.operation(catalog, "data.catalog")["output"]["contract"] = "plenora-data-kernel-catalog-v9"
        self.assertTrue(gate_fails(load_catalog_versions=self.mutated_versions(1, mutate)))

    def test_gate_rejects_a_catalog_claiming_another_profile(self):
        def mutate(catalog):
            catalog["profile"] = "plenora-data-tools-profile-v1"
        self.assertTrue(gate_fails(load_catalog_versions=self.mutated_versions(2, mutate)))

    def test_gate_rejects_run_on_runtime(self):
        def mutate(catalog):
            self.operation(catalog, "data.run")["surfaces"].append("runtime")
        self.assertTrue(gate_fails(load_catalog_versions=self.mutated_versions(2, mutate)))

    def test_gate_rejects_an_invalid_plan_example(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("examples/valid/data-plan-v1.json"):
                document = copy.deepcopy(document)
                document["outputs"] = ["nowhere"]
            return document

        self.assertTrue(gate_fails(load_json=loader))

    def test_gate_rejects_bindings_without_artifact(self):
        original = validator.load_json

        def loader(path):
            document = original(path)
            if str(path).replace("\\", "/").endswith("bindings/python-sdk-v1.json"):
                document = json.loads(json.dumps(document))
                section = next(item for item in document["components"] if item["component"] == validator.DATA_COMPONENT)
                section["artifact"] = None
            return document

        self.assertTrue(gate_fails(load_json=loader))

    def test_gate_rejects_a_repeated_identity_with_another_contract(self):
        def mutate(catalog):
            self.operation(catalog, "data.describe")["output"]["contract"] = "plenora-data-description-v99"
        self.assertTrue(gate_fails(load_catalog_versions=self.mutated_versions(1, mutate)))

    def test_a_spelling_shared_inside_one_catalog_is_rejected(self):
        # Il catalogo v2 seleziona anche data.validate@1: la grafia condivisa
        # con @2 diventa ambigua per un artefatto v2.
        catalogs = copy.deepcopy(self.catalogs)
        extra = copy.deepcopy(self.operation(self.versions[validator.DATA_COMPONENT][1], "data.validate"))
        catalogs[validator.DATA_COMPONENT]["operations"].append(extra)
        errors = validator.validate_bindings(catalogs)
        self.assertTrue(any("spelling" in error for error in errors), errors)

    def test_non_json_constants_are_rejected(self):
        self.assertTrue(validator.data_plan_number_errors('{"a": NaN}'))
        self.assertTrue(validator.data_plan_number_errors('{"a": -Infinity}'))
        with self.assertRaises(ValueError):
            validator.reject_constant("NaN")


if __name__ == "__main__":
    unittest.main()
