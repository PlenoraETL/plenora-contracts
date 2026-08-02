from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc
from shapely.geometry import Polygon

from conformance.judge_plenora_cross import build_report


class PlenoraCrossJudgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        plenora = pa.table(
            {
                "id": pa.array([1, 2], type=pa.int64()),
                "value": pa.array([1.0, 2.0], type=pa.float64()),
                "label": pa.array(["one", "two"], type=pa.large_string()),
            }
        )
        data = pa.table(
            {
                "id": pa.array([1, 2], type=pa.int64()),
                "value": pa.array([1, 2], type=pa.int64()),
                "label": pa.array(["one", "two"], type=pa.string()),
            }
        )
        self.write_table("plenora-filter.arrow", plenora)
        self.write_table("data-filter.arrow", data)
        polygons = [
            Polygon([(9.0, 45.0), (9.1, 45.0), (9.1, 45.1), (9.0, 45.0)]),
            Polygon([(9.2, 45.2), (9.3, 45.2), (9.3, 45.3), (9.2, 45.2)]),
        ]
        geometry = pa.field(
            "geometry",
            pa.binary(),
            metadata={
                b"plenora.geometry.crs_id": b"EPSG:4326",
                b"plenora.geometry.srid": b"4326",
            },
        )
        table = pa.Table.from_arrays(
            [pa.array([item.wkb for item in polygons]), pa.array([1, 2])],
            schema=pa.schema([geometry, pa.field("id", pa.int64())]),
        )
        self.write_table("data-reproject.arrow", table)
        self.write_plenora_geometry(polygons)
        self.spec = {
            "campaign_id": "plenora-read-only-cross-v1",
            "plenora_revision": "f" * 40,
            "data_revision": "a" * 40,
            "filter": {
                "allowed_contract_differences": [
                    {
                        "category": "contract",
                        "path": "fields[1].type",
                        "before": "double",
                        "after": "int64",
                    },
                    {
                        "category": "contract",
                        "path": "fields[2].type",
                        "before": "large_string",
                        "after": "string",
                    },
                ]
            },
            "reproject": {
                "crs": "EPSG:4326",
                "hausdorff_tolerance_degrees": 1e-10,
            },
        }

    def tearDown(self) -> None:
        self.directory.cleanup()

    def write_table(self, name: str, table: pa.Table) -> None:
        with ipc.new_file(self.root / name, table.schema) as writer:
            writer.write_table(table)

    def write_plenora_geometry(self, polygons: list[Polygon]) -> None:
        (self.root / "plenora-reproject.json").write_text(
            json.dumps(
                {
                    "rows": len(polygons),
                    "crs": "EPSG:4326",
                    "geometries": [{"wkb_hex": item.wkb_hex} for item in polygons],
                }
            ),
            encoding="utf-8",
        )

    def test_declared_physical_differences_and_equivalent_geometry_pass(self) -> None:
        report = build_report(self.spec, self.root)

        self.assertEqual(report["status"], "pass_with_declared_differences")
        self.assertEqual(report["filter"]["logical_values"], "pass")
        self.assertEqual(report["filter"]["undeclared_contract_differences"], [])
        self.assertLessEqual(report["reproject"]["max_hausdorff_degrees"], 1e-10)

    def test_geometry_outside_tolerance_fails(self) -> None:
        self.write_plenora_geometry(
            [
                Polygon([(10.0, 45.0), (10.1, 45.0), (10.1, 45.1), (10.0, 45.0)]),
                Polygon([(9.2, 45.2), (9.3, 45.2), (9.3, 45.3), (9.2, 45.2)]),
            ]
        )

        report = build_report(self.spec, self.root)

        self.assertEqual(report["status"], "fail")
        self.assertGreater(report["reproject"]["max_hausdorff_degrees"], 1e-10)


if __name__ == "__main__":
    unittest.main()
