from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc

from conformance.comparator import compare_ipc


def write_batches(path: Path, schema: pa.Schema, batches: list[pa.RecordBatch]) -> None:
    with ipc.new_file(path, schema) as writer:
        for batch in batches:
            writer.write_batch(batch)


def base_schema(*, schema_metadata: dict[bytes, bytes] | None = None) -> pa.Schema:
    return pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field(
                "primary_shape",
                pa.binary(),
                metadata={
                    b"plenora.field_id": b"primary-shape",
                    b"plenora.geometry.encoding": b"ewkb",
                },
            ),
            pa.field(
                "secondary_shape",
                pa.binary(),
                metadata={
                    b"plenora.field_id": b"secondary-shape",
                    b"plenora.geometry.encoding": b"wkb",
                },
            ),
        ],
        metadata=schema_metadata or {b"plenora.contract.version": b"2.0-rc16"},
    )


def batch(schema: pa.Schema, rows: list[tuple[int, bytes | None, bytes | None]]) -> pa.RecordBatch:
    return pa.RecordBatch.from_arrays(
        [
            pa.array([row[0] for row in rows], type=pa.int64()),
            pa.array([row[1] for row in rows], type=pa.binary()),
            pa.array([row[2] for row in rows], type=pa.binary()),
        ],
        schema=schema,
    )


SEMANTIC_POLICY = {
    "artifact_byte": False,
    "batch_structure": False,
    "contract": True,
    "values": True,
}

STRICT_POLICY = {
    "artifact_byte": True,
    "batch_structure": True,
    "contract": True,
    "values": True,
}


class IpcComparatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.before = self.root / "before.arrow"
        self.after = self.root / "after.arrow"

    def tearDown(self) -> None:
        self.directory.cleanup()

    def write_pair(
        self,
        before_schema: pa.Schema,
        before_batches: list[pa.RecordBatch],
        after_schema: pa.Schema | None = None,
        after_batches: list[pa.RecordBatch] | None = None,
    ) -> None:
        write_batches(self.before, before_schema, before_batches)
        write_batches(
            self.after,
            after_schema or before_schema,
            after_batches if after_batches is not None else before_batches,
        )

    def test_exact_copy_passes_strict_policy(self) -> None:
        schema = base_schema()
        rows = [(1, b"a", b"b"), (2, None, b"c")]
        self.write_pair(schema, [batch(schema, rows)])
        report = compare_ipc(self.before, self.after, STRICT_POLICY)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["differences"], [])

    def test_added_schema_metadata_is_detected_symmetrically(self) -> None:
        before_schema = base_schema()
        after_schema = base_schema(
            schema_metadata={
                b"plenora.contract.version": b"2.0-rc16",
                b"unexpected": b"added",
            }
        )
        rows = [(1, b"a", b"b")]
        self.write_pair(
            before_schema,
            [batch(before_schema, rows)],
            after_schema,
            [batch(after_schema, rows)],
        )
        report = compare_ipc(self.before, self.after, SEMANTIC_POLICY)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                diff["category"] == "contract"
                and "schema.metadata" in diff["path"]
                and diff["before"] is None
                for diff in report["differences"]
            )
        )

    def test_metadata_on_second_geometry_field_is_not_flattened_or_ignored(self) -> None:
        before_schema = base_schema()
        fields = list(before_schema)
        fields[2] = fields[2].with_metadata(
            {
                **(fields[2].metadata or {}),
                b"plenora.geometry.encoding": b"ewkb",
            }
        )
        after_schema = pa.schema(fields, metadata=before_schema.metadata)
        rows = [(1, b"a", b"b")]
        self.write_pair(
            before_schema,
            [batch(before_schema, rows)],
            after_schema,
            [batch(after_schema, rows)],
        )
        report = compare_ipc(self.before, self.after, SEMANTIC_POLICY)
        self.assertTrue(
            any(
                diff["category"] == "contract"
                and "fields[2].metadata" in diff["path"]
                for diff in report["differences"]
            )
        )

    def test_one_bit_binary_payload_change_is_detected(self) -> None:
        schema = base_schema()
        self.write_pair(
            schema,
            [batch(schema, [(1, b"\x00\x01", b"same")])],
            schema,
            [batch(schema, [(1, b"\x00\x00", b"same")])],
        )
        report = compare_ipc(self.before, self.after, SEMANTIC_POLICY)
        self.assertTrue(
            any(diff["category"] == "values" for diff in report["differences"])
        )

    def test_row_reordering_is_detected(self) -> None:
        schema = base_schema()
        rows = [(1, b"a", b"b"), (2, b"c", b"d")]
        self.write_pair(
            schema,
            [batch(schema, rows)],
            schema,
            [batch(schema, list(reversed(rows)))],
        )
        report = compare_ipc(self.before, self.after, SEMANTIC_POLICY)
        self.assertTrue(
            any(diff["category"] == "values" for diff in report["differences"])
        )

    def test_field_order_and_nullability_are_contract_properties(self) -> None:
        before_schema = base_schema()
        after_schema = pa.schema(
            [
                pa.field("primary_shape", pa.binary()),
                pa.field("id", pa.int64(), nullable=True),
                pa.field("secondary_shape", pa.binary()),
            ],
            metadata=before_schema.metadata,
        )
        self.write_pair(
            before_schema,
            [batch(before_schema, [(1, b"a", b"b")])],
            after_schema,
            [
                pa.RecordBatch.from_arrays(
                    [pa.array([b"a"]), pa.array([1]), pa.array([b"b"])],
                    schema=after_schema,
                )
            ],
        )
        report = compare_ipc(self.before, self.after, SEMANTIC_POLICY)
        contract_paths = {
            diff["path"]
            for diff in report["differences"]
            if diff["category"] == "contract"
        }
        self.assertIn("fields[0].name", contract_paths)
        self.assertIn("fields[0].nullable", contract_paths)

    def test_batch_only_difference_passes_semantic_but_not_strict_policy(self) -> None:
        schema = base_schema()
        rows = [(1, b"a", b"b"), (2, b"c", b"d")]
        self.write_pair(
            schema,
            [batch(schema, rows)],
            schema,
            [batch(schema, rows[:1]), batch(schema, rows[1:])],
        )
        semantic = compare_ipc(self.before, self.after, SEMANTIC_POLICY)
        strict = compare_ipc(self.before, self.after, STRICT_POLICY)
        self.assertEqual(semantic["status"], "pass")
        self.assertEqual(semantic["differences"], [])
        self.assertEqual(strict["status"], "fail")
        self.assertTrue(
            any(
                diff["category"] in {"artifact_byte", "batch_structure"}
                for diff in strict["differences"]
            )
        )

    def test_nested_field_metadata_change_is_detected(self) -> None:
        before_child = pa.field(
            "shape",
            pa.binary(),
            metadata={b"plenora.geometry.encoding": b"wkb"},
        )
        after_child = before_child.with_metadata(
            {b"plenora.geometry.encoding": b"ewkb"}
        )
        before_schema = pa.schema([pa.field("payload", pa.struct([before_child]))])
        after_schema = pa.schema([pa.field("payload", pa.struct([after_child]))])
        before_batch = pa.RecordBatch.from_arrays(
            [pa.array([{"shape": b"same"}], type=before_schema[0].type)],
            schema=before_schema,
        )
        after_batch = pa.RecordBatch.from_arrays(
            [pa.array([{"shape": b"same"}], type=after_schema[0].type)],
            schema=after_schema,
        )
        self.write_pair(
            before_schema,
            [before_batch],
            after_schema,
            [after_batch],
        )

        report = compare_ipc(self.before, self.after, SEMANTIC_POLICY)

        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                difference["category"] == "contract"
                and difference["path"]
                == "fields[0].children[0].metadata['plenora.geometry.encoding']"
                for difference in report["differences"]
            )
        )

    def test_logically_equal_values_pass_when_only_physical_types_differ(self) -> None:
        before_schema = pa.schema([pa.field("label", pa.string())])
        after_schema = pa.schema([pa.field("label", pa.large_string())])
        self.write_pair(
            before_schema,
            [
                pa.RecordBatch.from_arrays(
                    [pa.array(["a", "b"])], schema=before_schema
                )
            ],
            after_schema,
            [
                pa.RecordBatch.from_arrays(
                    [pa.array(["a", "b"], type=pa.large_string())],
                    schema=after_schema,
                )
            ],
        )
        values_only = {
            "artifact_byte": False,
            "batch_structure": False,
            "contract": False,
            "values": True,
        }

        report = compare_ipc(self.before, self.after, values_only)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            report["before"]["values_sha256"],
            report["after"]["values_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
