"""SB-001: the effect a surface adds to an operation is declared in the
capability `attributes` as `plenora.surface_side_effects` (decision 0009)."""

import json
import unittest
from pathlib import Path

from conformance_checks import capability_errors

ROOT = Path(__file__).resolve().parents[1]
KEY = "plenora.surface_side_effects"


def document_with(effects, side_effect="none"):
    document = json.loads(
        (ROOT / "examples/valid/capabilities-v2-surface-side-effects.json").read_text(encoding="utf-8")
    )
    for operation in document["operations"]:
        if operation["id"] == "io.read":
            operation["side_effect"] = side_effect
            operation["attributes"] = {KEY: effects}
    return document


def sb001(document):
    return [error for error in capability_errors(document) if "SB-001" in error]


class SurfaceSideEffectTests(unittest.TestCase):
    def test_declared_stricter_effect_passes(self):
        self.assertEqual(capability_errors(document_with({"cli": "local"})), [])
        self.assertEqual(capability_errors(document_with({"cli": "remote"}, "local")), [])

    def test_effect_not_stricter_than_the_operation_is_rejected(self):
        self.assertTrue(sb001(document_with({"cli": "none"})))
        self.assertTrue(sb001(document_with({"cli": "local"}, "local")))
        self.assertTrue(sb001(document_with({"cli": "local"}, "remote")))

    def test_surface_the_operation_does_not_list_is_rejected(self):
        self.assertTrue(sb001(document_with({"runtime": "local"})))

    def test_values_outside_the_vocabulary_are_rejected(self):
        for value in ("Local", None, 1, ["local"]):
            self.assertTrue(sb001(document_with({"cli": value})), value)

    def test_value_that_is_not_a_non_empty_object_is_rejected(self):
        for effects in ({}, None, "local", ["cli"]):
            self.assertTrue(sb001(document_with(effects)), effects)

    def test_other_reserved_attribute_keys_are_rejected(self):
        document = document_with({"cli": "local"})
        for operation in document["operations"]:
            if operation["id"] == "io.read":
                operation["attributes"]["plenora.formats"] = ["gpkg"]
        self.assertTrue(any("CAP-013" in error for error in capability_errors(document)))

    def test_component_attributes_stay_opaque(self):
        document = document_with({"cli": "local"})
        for operation in document["operations"]:
            if operation["id"] == "io.read":
                operation["attributes"]["formats"] = ["gpkg"]
        self.assertEqual(capability_errors(document), [])


if __name__ == "__main__":
    unittest.main()
