"""IO-tools profile version 2 (decision 0011).

A profile that lists its component-owned wire contracts lists exactly the
pairs of its catalog version; a pair copied from version 1 would name a
result the artifact does not emit.
"""

import json
import unittest

import validate_specs as validator

ROOT = validator.ROOT


def catalog(version):
    return json.loads((ROOT / f"catalogs/io-tools-v{version}.json").read_text(encoding="utf-8"))


def profile(name):
    return (ROOT / "profiles" / name).read_text(encoding="utf-8")


class WireContractTests(unittest.TestCase):
    def test_both_io_profiles_list_their_catalog_pairs(self):
        self.assertEqual(validator.wire_contract_errors(profile("io-tools.md"), catalog(1)), [])
        self.assertEqual(validator.wire_contract_errors(profile("io-tools-v2.md"), catalog(2)), [])

    def test_pair_of_another_version_is_rejected(self):
        text = profile("io-tools-v2.md").replace(
            "`plenora-io-read-input-v1` and `plenora-io-read-result-v2`",
            "`plenora-io-read-input-v1` and `plenora-io-read-result-v1`",
        )
        errors = validator.wire_contract_errors(text, catalog(2))
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("plenora-io-read-result-v1" in error for error in errors))
        self.assertTrue(any("plenora-io-read-result-v2" in error for error in errors))

    def test_version_1_profile_does_not_describe_version_2(self):
        self.assertEqual(
            len(validator.wire_contract_errors(profile("io-tools.md"), catalog(2))), 6
        )

    def test_profile_without_the_section_is_not_checked(self):
        self.assertEqual(validator.wire_contract_errors("# Profile\n\n## Scope\n", catalog(2)), [])


class CatalogVersionTwoTests(unittest.TestCase):
    def test_three_operations_change_version_and_output(self):
        versions = {
            operation["id"]: (operation["version"], operation["output"]["contract"])
            for operation in catalog(2)["operations"]
        }
        self.assertEqual(versions["io.read"], (2, "plenora-io-read-result-v2"))
        self.assertEqual(versions["io.write"], (2, "plenora-io-write-result-v2"))
        self.assertEqual(versions["io.catalog"], (2, "plenora-io-catalog-v2"))
        for name in ("io.inspect", "io.layers", "io.convert"):
            self.assertEqual(versions[name][0], 1)

    def test_version_2_inputs_are_those_of_version_1(self):
        before = {op["id"]: op["input"] for op in catalog(1)["operations"]}
        for operation in catalog(2)["operations"]:
            self.assertEqual(operation["input"], before[operation["id"]], operation["id"])


if __name__ == "__main__":
    unittest.main()
