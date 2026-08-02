from __future__ import annotations

import unittest

from conformance.corpus.generate import CASES, EPSG_3003_WKT_TOWGS84
from conformance.realdata.generate_patrimonial import pathology_for


class CadastralCorpusRegressionTests(unittest.TestCase):
    def test_epsg_axis_case_declares_authority_derived_srid_completion(self) -> None:
        table, expected = CASES["axis_lat_lon"]()
        metadata = {
            key.decode(): value.decode()
            for key, value in (table.schema.field(0).metadata or {}).items()
        }
        self.assertEqual(metadata["plenora.geometry.crs_id"], "EPSG:4326")
        self.assertNotIn("plenora.geometry.srid", metadata)
        self.assertEqual(
            expected["allowed_transitions"],
            [
                {
                    "category": "contract",
                    "path": "fields[0].metadata['plenora.geometry.srid']",
                    "before": None,
                    "after": "4326",
                    "reason": "authority_derived_srid_completion",
                }
            ],
        )

    def test_towgs84_bound_crs_case_is_mandatory(self) -> None:
        self.assertIn("crs_wkt_towgs84", CASES)
        table, expected = CASES["crs_wkt_towgs84"]()
        metadata = {
            key.decode(): value.decode()
            for key, value in (table.schema.field(0).metadata or {}).items()
        }
        self.assertIn("TOWGS84[", EPSG_3003_WKT_TOWGS84)
        self.assertEqual(
            metadata["plenora.geometry.crs_definition"],
            EPSG_3003_WKT_TOWGS84,
        )
        self.assertEqual(metadata["plenora.geometry.crs_id"], "EPSG:3003")
        self.assertEqual(metadata["plenora.geometry.crs_resolution"], "resolved")
        self.assertEqual(metadata["plenora.geometry.axis_order"], "easting_northing")
        self.assertNotIn("plenora.geometry.srid", metadata)
        self.assertEqual(expected["crs_definition_format"], "wkt")
        self.assertEqual(
            expected["allowed_transitions"],
            [
                {
                    "category": "contract",
                    "path": "fields[0].metadata['plenora.geometry.srid']",
                    "before": None,
                    "after": "3003",
                    "reason": "authority_derived_srid_completion",
                }
            ],
        )

    def test_geometrie_sane_only_removes_geometric_pathologies(self) -> None:
        for index in range(200):
            self.assertEqual(pathology_for(index, geometrie_sane=True), "regolare")
        self.assertTrue(
            any(pathology_for(index) != "regolare" for index in range(200)),
            "the default corpus must retain geometric pathologies",
        )


if __name__ == "__main__":
    unittest.main()
