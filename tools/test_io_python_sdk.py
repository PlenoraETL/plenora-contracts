"""IO-tools Python SDK (decision 0016): the catalog selects the surface as
conditional, every operation of catalog version 2 lists it, and the binding
map names `Client` methods with version and capability discovery."""

import copy
import json
import unittest

import validate_specs as validator

ROOT = validator.ROOT


def python_document():
    return json.loads((ROOT / "bindings/python-sdk-v1.json").read_text(encoding="utf-8"))


def io_section(document):
    return next(item for item in document["components"] if item["component"] == validator.IO_COMPONENT)


class IoPythonSdkTests(unittest.TestCase):
    def test_catalog_selects_the_surface_for_every_operation(self):
        catalog = json.loads((ROOT / "catalogs/io-tools-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["target_surfaces"]["python_sdk"], "conditional")
        for operation in catalog["operations"]:
            self.assertIn("python_sdk", operation["surfaces"], operation["id"])
        version_1 = json.loads((ROOT / "catalogs/io-tools-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(version_1["target_surfaces"]["python_sdk"], "not_applicable")

    def test_published_binding_passes(self):
        self.assertEqual(validator.io_python_errors(python_document()), [])
        self.assertEqual(validator.validate_bindings(validator.load_catalogs()), [])

    def test_identity_discovery_and_spelling_are_checked(self):
        document = python_document()
        section = io_section(document)
        section["artifact"] = "plenora-io-tools / plenora_io"
        section["discovery"] = ["plenora_io.version"]
        section["bindings"][0]["entrypoints"] = ["catalog"]
        errors = validator.io_python_errors(document)
        self.assertEqual(len(errors), 3)

    def test_a_non_client_spelling_is_rejected(self):
        document = python_document()
        read = next(item for item in io_section(document)["bindings"] if item["operation"] == "io.read")
        read["entrypoints"].append("plenora_io.read")
        self.assertEqual(len(validator.io_python_errors(document)), 1)

    def test_an_empty_section_is_not_checked(self):
        document = python_document()
        section = io_section(document)
        section.update(artifact=None, discovery=[], bindings=[])
        self.assertEqual(validator.io_python_errors(document), [])
        document["components"] = [
            item for item in document["components"] if item["component"] != validator.IO_COMPONENT
        ]
        self.assertEqual(validator.io_python_errors(copy.deepcopy(document)), [])


if __name__ == "__main__":
    unittest.main()
