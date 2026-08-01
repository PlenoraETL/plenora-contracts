from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.ipc as ipc

from conformance._shared import (
    contract_from_stdout_scoped,
    diff,
    judge_ipc_transition,
    judge_transition,
    observe,
    observe_scoped,
)


class SharedTransitionTests(unittest.TestCase):
    @staticmethod
    def _write(path: Path, table: pa.Table) -> None:
        with ipc.new_file(path, table.schema) as writer:
            writer.write_table(table)

    def test_ipc_transition_rejects_value_corruption(self) -> None:
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.arrow"
            after = Path(directory) / "after.arrow"
            self._write(before, pa.table({"id": [1], "value": ["original"]}))
            self._write(after, pa.table({"id": [1], "value": ["corrupt"]}))

            passed, reason, differences = judge_ipc_transition(
                before, after, {}, None
            )

        self.assertFalse(passed)
        self.assertIn("values", reason)
        self.assertTrue(any(row["category"] == "values" for row in differences))

    def test_ipc_transition_rejects_non_geometry_contract_change(self) -> None:
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.arrow"
            after = Path(directory) / "after.arrow"
            self._write(before, pa.table({"id": pa.array([1], pa.int64())}))
            self._write(after, pa.table({"id": pa.array([1], pa.int32())}))

            passed, reason, differences = judge_ipc_transition(
                before, after, {}, None
            )

        self.assertFalse(passed)
        self.assertIn("forbidden_transition", reason)
        self.assertTrue(any(row["path"] == "fields[0].type" for row in differences))

    def test_allowed_and_required_transitions_cannot_be_mixed(self) -> None:
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.arrow"
            self._write(before, pa.table({"id": [1]}))
            expected = {
                "allowed_transitions": [
                    {
                        "category": "contract",
                        "path": "fields[0].metadata['x']",
                        "before": None,
                        "after": "1",
                        "reason": "optional",
                    }
                ],
                "required_transitions": {
                    "transformation_core": {
                        "x": {"from": None, "to": "1"}
                    }
                },
            }

            passed, reason, _ = judge_ipc_transition(
                before, before, expected, "transformation_core"
            )

        self.assertFalse(passed)
        self.assertIn("both allowed_transitions and required_transitions", reason)

    def test_allowed_transition_need_not_be_produced_by_every_stage(self) -> None:
        expected = {
            "allowed_transitions": [
                {
                    "category": "contract",
                    "path": "fields[0].metadata['plenora.geometry.srid']",
                    "before": None,
                    "after": "4326",
                    "reason": "authority_derived_srid_completion",
                }
            ]
        }

        passed, _, residual = judge_transition(expected, "file_boundary", [])

        self.assertTrue(passed)
        self.assertEqual(residual, [])

    def test_diff_reports_added_metadata_symmetrically(self) -> None:
        before = {"schema": {}, "field": {}}
        after = {"schema": {}, "field": {"plenora.geometry.srid": "3003"}}

        self.assertEqual(
            diff(before, after),
            ["plenora.geometry.srid: None -> '3003'"],
        )

    def test_declared_transition_uses_fail_closed_fidelity_judge(self) -> None:
        expected = {
            "required_transitions": {
                "engine": {
                    "plenora.geometry.srid": {
                        "from": None,
                        "to": "3003",
                        "reason": "authority_derived_srid_completion",
                    }
                }
            }
        }
        observed = ["plenora.geometry.srid: None -> '3003'"]

        passed, _, residual = judge_transition(expected, "engine", observed)

        self.assertTrue(passed)
        self.assertEqual(residual, [])

    def test_undeclared_transition_fails(self) -> None:
        passed, reason, residual = judge_transition(
            {"required_transitions": {"engine": {}}},
            "engine",
            ["unexpected: None -> 'value'"],
        )

        self.assertFalse(passed)
        self.assertIn("forbidden_transition", reason)
        self.assertTrue(residual)

    def test_corpus_field_metadata_path_is_normalized_for_shared_observer(self) -> None:
        expected = {
            "allowed_transitions": [
                {
                    "category": "contract",
                    "path": "fields[0].metadata['plenora.geometry.srid']",
                    "before": None,
                    "after": "3003",
                    "reason": "authority_derived_srid_completion",
                }
            ]
        }

        passed, _, residual = judge_transition(
            expected,
            "engine",
            ["plenora.geometry.srid: None -> '3003'"],
        )

        self.assertTrue(passed)
        self.assertEqual(residual, [])

    def test_scoped_observer_keeps_same_metadata_key_on_distinct_fields(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scoped.arrow"
            schema = pa.schema(
                [
                    pa.field("first", pa.int64(), metadata={"shared": "one"}),
                    pa.field("second", pa.int64(), metadata={"shared": "two"}),
                ]
            )
            self._write(path, pa.table({"first": [1], "second": [2]}, schema=schema))

            arrow_contract = observe_scoped(path)
            cli_contract = contract_from_stdout_scoped(
                '{"fields":[{"metadata":{"shared":"one"}},'
                '{"metadata":{"shared":"two"}}]}'
            )

        self.assertEqual(arrow_contract, cli_contract)
        self.assertEqual(arrow_contract["fields[0].metadata['shared']"], "one")
        self.assertEqual(arrow_contract["fields[1].metadata['shared']"], "two")


if __name__ == "__main__":
    unittest.main()
