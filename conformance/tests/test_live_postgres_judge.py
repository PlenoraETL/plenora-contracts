from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc

from conformance.judge_live_postgres import build_report


class LivePostgresJudgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.spec = {
            "campaign_id": "postgres-data-io-live-v1",
            "components": {
                "database": {"revision": "d" * 40},
                "data": {"revision": "a" * 40},
                "io": {"revision": "i" * 40},
            },
            "fixture": {"rows": 2},
            "required_transitions": [
                {
                    "category": "contract",
                    "path": "fields[1].metadata['plenora.field_id']",
                    "before": None,
                    "after": "1",
                    "reason": "deterministic field index",
                },
                {
                    "category": "contract",
                    "path": "fields[1].metadata['plenora.geometry.precision']",
                    "before": None,
                    "after": "float64",
                    "reason": "governed WKB precision",
                },
            ],
            "fault_cases": [
                {
                    "id": "rows_over_budget",
                    "required_category": "resource_limit",
                    "required_remote_effect": "rolled_back",
                    "artifact_must_not_exist": True,
                }
            ],
        }
        self.events = {
            "executed_at": "2026-08-01",
            "source_rows_observed_after_export": 2,
            "data": {
                "exit_code": 0,
                "output_preexisting": False,
                "rows_in": 2,
                "rows_out": 2,
                "spill_bytes": 0,
            },
            "io": {
                "exit_code": 0,
                "output_preexisting": False,
                "rows": 2,
                "expected_loss": {},
                "observed_loss": {},
                "reported_loss": {},
            },
            "faults": [
                {
                    "id": "rows_over_budget",
                    "exit_code": 2,
                    "category": "resource_limit",
                    "remote_effect": "rolled_back",
                    "artifact_exists": False,
                }
            ],
        }
        base_schema = pa.schema(
            [
                pa.field("id", pa.int64(), nullable=False),
                pa.field("geom", pa.binary()),
            ],
            metadata={b"plenora.contract.version": b"1"},
        )
        self.base_schema = base_schema
        self.write("postgres-1.arrow", base_schema)
        self.write("postgres-2.arrow", base_schema)
        self.write("data.arrow", base_schema)
        io_fields = list(base_schema)
        io_fields[1] = io_fields[1].with_metadata(
            {
                b"plenora.field_id": b"1",
                b"plenora.geometry.precision": b"float64",
            }
        )
        self.write("io.arrow", pa.schema(io_fields, metadata=base_schema.metadata))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def write(self, name: str, schema: pa.Schema) -> None:
        batch = pa.RecordBatch.from_arrays(
            [pa.array([1, 2]), pa.array([b"a", b"b"])],
            schema=schema,
        )
        with ipc.new_file(self.artifacts / name, schema) as writer:
            writer.write_batch(batch)

    def test_exact_live_observation_builds_passing_report(self) -> None:
        report = build_report(self.spec, self.events, self.artifacts)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["database_export"]["determinism"], "byte_exact")
        self.assertEqual(report["database_to_data"]["status"], "pass")
        self.assertEqual(report["data_to_io"]["transition_judge"], "pass")
        self.assertEqual(report["data_to_io"]["reported_loss"], {})
        self.assertEqual(report["persistent_database_roundtrip"], "not_demonstrated")
        self.assertNotIn("durability", json.dumps(report))

    def test_undeclared_io_metadata_forces_failure(self) -> None:
        schema = ipc.open_file(self.artifacts / "io.arrow").schema
        fields = list(schema)
        fields[1] = fields[1].with_metadata(
            {**(fields[1].metadata or {}), b"unexpected": b"value"}
        )
        self.write("io.arrow", pa.schema(fields, metadata=schema.metadata))

        report = build_report(self.spec, self.events, self.artifacts)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["data_to_io"]["transition_judge"], "fail")

    def test_failed_or_stale_live_stage_forces_failure(self) -> None:
        mutations = (
            ("data", "exit_code", 2),
            ("io", "exit_code", 2),
            ("data", "output_preexisting", True),
            ("io", "output_preexisting", True),
        )
        for stage, key, value in mutations:
            with self.subTest(stage=stage, key=key):
                events = json.loads(json.dumps(self.events))
                events[stage][key] = value

                report = build_report(self.spec, events, self.artifacts)

                self.assertEqual(report["status"], "fail")
                self.assertIn(f"{stage}_{key}", " ".join(report["issues"]))

    def test_missing_stage_execution_field_forces_failure(self) -> None:
        events = json.loads(json.dumps(self.events))
        del events["data"]["exit_code"]

        report = build_report(self.spec, events, self.artifacts)

        self.assertEqual(report["status"], "fail")
        self.assertIn("data_exit_code", " ".join(report["issues"]))


if __name__ == "__main__":
    unittest.main()
