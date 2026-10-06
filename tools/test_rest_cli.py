"""REST CLI as an optional (conditional) surface.

A REST capability document lists every required target surface, may omit a
conditional one (the CLI) and may not list a surface its catalog does not
select. Before, the surfaces had to equal the catalog's: a conditional CLI in
the catalog would have made every artifact without the command invalid.
"""

import copy
import json
import unittest

import validate_specs as validator

ROOT = validator.ROOT


def rest_catalog():
    return json.loads((ROOT / "catalogs/rest-tools-v1.json").read_text(encoding="utf-8"))


def capability(surfaces):
    document = json.loads(
        (ROOT / "examples/valid/capabilities-rest-v2.json").read_text(encoding="utf-8")
    )
    for operation in document["operations"]:
        operation["surfaces"] = list(surfaces)
    return document


def surface_errors(document, catalog):
    return [
        error for error in validator.rest_capability_errors(document, catalog)
        if "surfaces differ" in error
    ]


class RestCapabilitySurfaceTests(unittest.TestCase):
    def test_artifact_without_the_cli_conforms(self):
        self.assertEqual(
            surface_errors(capability(["rust", "python_sdk", "runtime"]), rest_catalog()), []
        )

    def test_artifact_with_the_cli_conforms(self):
        self.assertEqual(
            surface_errors(capability(["rust", "cli", "python_sdk", "runtime"]), rest_catalog()), []
        )

    def test_missing_required_surface_is_rejected(self):
        self.assertEqual(
            len(surface_errors(capability(["rust", "cli", "python_sdk"]), rest_catalog())), 5
        )

    def test_surface_the_catalog_does_not_select_is_rejected(self):
        catalog = copy.deepcopy(rest_catalog())
        catalog["target_surfaces"]["cli"] = "not_applicable"
        for operation in catalog["operations"]:
            operation["surfaces"].remove("cli")
        self.assertEqual(
            len(surface_errors(capability(["rust", "cli", "python_sdk", "runtime"]), catalog)), 5
        )


class RestCliBindingTests(unittest.TestCase):
    def test_every_rest_operation_has_a_cli_spelling(self):
        document = json.loads((ROOT / "bindings/cli-v1.json").read_text(encoding="utf-8"))
        (section,) = [
            item for item in document["components"] if item["component"] == "plenora-rest-tools"
        ]
        self.assertEqual(section["artifact"], "plenora-rest")
        self.assertEqual(
            {binding["operation"] for binding in section["bindings"]},
            {"rest.test", "rest.generate", "rest.enrich", "rest.download", "rest.upload"},
        )


if __name__ == "__main__":
    unittest.main()
