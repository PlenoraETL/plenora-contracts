from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.ipc as ipc

from conformance._shared import judge_ipc_transition


class PairwiseTransitionTests(unittest.TestCase):
    @staticmethod
    def _write(path: Path, resolution: str) -> None:
        field = pa.field(
            "geometry",
            pa.binary(),
            metadata={"plenora.geometry.crs_resolution": resolution},
        )
        table = pa.table(
            {"geometry": [b"same"]},
            schema=pa.schema([field]),
        )
        with ipc.new_file(path, table.schema) as writer:
            writer.write_table(table)

    def test_required_transition_is_judged_at_producing_role(self) -> None:
        expected = {
            "required_transitions": {
                "transformation_core": {
                    "plenora.geometry.crs_resolution": {
                        "from": "resolved",
                        "to": "declared_unresolved",
                    }
                }
            }
        }
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.arrow"
            after = Path(directory) / "after.arrow"
            self._write(before, "resolved")
            self._write(after, "declared_unresolved")

            produced, _, _ = judge_ipc_transition(
                before, after, expected, "transformation_core"
            )
            preserved, _, _ = judge_ipc_transition(
                after, after, expected, "file_boundary"
            )

        self.assertTrue(produced)
        self.assertTrue(preserved)

    def test_transition_at_wrong_role_fails_closed(self) -> None:
        expected = {
            "required_transitions": {
                "transformation_core": {
                    "plenora.geometry.crs_resolution": {
                        "from": "resolved",
                        "to": "declared_unresolved",
                    }
                }
            }
        }
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.arrow"
            after = Path(directory) / "after.arrow"
            self._write(before, "resolved")
            self._write(after, "declared_unresolved")

            passed, reason, _ = judge_ipc_transition(
                before, after, expected, "file_boundary"
            )

        self.assertFalse(passed)
        self.assertIn("forbidden_transition", reason)


if __name__ == "__main__":
    unittest.main()
