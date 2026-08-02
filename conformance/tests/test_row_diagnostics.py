from __future__ import annotations

import json
import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "conformance" / "schemas" / "row-diagnostics-v1.schema.json"
VALIDATOR = ROOT / "conformance" / "row_diagnostics.py"
ICD = ROOT / "docs" / "PLENORA-CONTRATTI-TRASVERSALI.md"
COMPONENTS = ROOT / "conformance" / "components.json"


def complete_read_report() -> dict[str, object]:
    return {
        "contract": "plenora-row-diagnostics-v1",
        "scope": "read",
        "index_basis": "source_row_zero_based",
        "completeness": "complete",
        "observed_total": 2,
        "total": 2,
        "counts": {
            "shapefile.inner_ring_without_outer": 1,
            "shapefile.unclosed_ring": 1,
        },
        "examples_limit": 10,
        "examples_truncated": False,
        "examples": [
            {
                "source_index": 17,
                "cause": "shapefile.inner_ring_without_outer",
                "key": {
                    "field": "parcel_id",
                    "state": "value",
                    "value": "A-0017",
                },
            },
            {
                "source_index": 89,
                "cause": "shapefile.unclosed_ring",
                "key": {
                    "field": "parcel_id",
                    "state": "redacted",
                },
            },
        ],
    }


def partial_write_report() -> dict[str, object]:
    return {
        "contract": "plenora-row-diagnostics-v1",
        "scope": "write",
        "index_basis": "source_row_zero_based",
        "completeness": "complete",
        "observed_total": 1,
        "total": 1,
        "input_total": 5_200,
        "counts": {"mysql.constraint_violation": 1},
        "examples_limit": 10,
        "examples_truncated": False,
        "examples": [
            {
                "source_index": 4_999,
                "cause": "mysql.constraint_violation",
                "write_state": "certainly_rejected",
                "key": {
                    "field": "parcel_id",
                    "state": "value",
                    "value": "P-5000",
                },
            }
        ],
        "diagnostic_state_counts": {
            "certainly_rejected": 1,
            "certainly_not_attempted": 0,
            "certainly_rolled_back": 0,
            "effect_unknown": 0,
        },
        "write_outcome": {
            "certainly_rejected": {"state": "known", "value": 1},
            "certainly_not_attempted": {"state": "known", "value": 200},
            "certainly_rolled_back": {"state": "unknown"},
            "effect_unknown": {"state": "unknown"},
        },
    }


def rolled_back_write_report() -> dict[str, object]:
    report = partial_write_report()
    report["completeness"] = "complete"
    report["total"] = 1
    report["write_outcome"] = {
        "certainly_rejected": {"state": "known", "value": 1},
        "certainly_not_attempted": {"state": "known", "value": 200},
        "certainly_rolled_back": {"state": "known", "value": 4_999},
        "effect_unknown": {"state": "known", "value": 0},
    }
    return report


class RowDiagnosticsSchemaTests(unittest.TestCase):
    def test_complete_read_rejection_is_schema_valid(self) -> None:
        self.assertTrue(SCHEMA.is_file(), "row diagnostics schema is required")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertEqual(errors, [])

    def test_partial_report_can_have_exact_aggregates_without_row_identity(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()
        report["completeness"] = "partial"
        report["knowledge_limits"] = ["row_identity_unavailable"]
        report["examples"] = []
        report["examples_truncated"] = False

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertEqual(errors, [])

        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate_report(report)

    def test_partial_known_total_cannot_be_less_than_observed_total(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["completeness"] = "partial"
        report["knowledge_limits"] = ["scan_incomplete"]
        report["total"] = 1

        with self.assertRaisesRegex(ValueError, "less than observed_total"):
            module.validate_report(report)

    def test_complete_report_fills_available_example_capacity(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["examples"] = report["examples"][:1]

        with self.assertRaisesRegex(ValueError, "complete report must provide"):
            module.validate_report(report)

    def test_unknown_report_can_declare_unobservable_cardinality(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()
        report["completeness"] = "unknown"
        report["knowledge_limits"] = [
            "cardinality_unavailable",
            "row_identity_unavailable",
        ]
        report.pop("total")
        report["observed_total"] = 0
        report["counts"] = {}
        report["examples"] = []
        report["examples_truncated"] = False

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertEqual(errors, [])

        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate_report(report)

    def test_completeness_state_controls_limits_and_total(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        partial_without_limit = complete_read_report()
        partial_without_limit["completeness"] = "partial"
        unknown_with_total = complete_read_report()
        unknown_with_total["completeness"] = "unknown"
        unknown_with_total["knowledge_limits"] = ["cardinality_unavailable"]
        complete_with_limit = complete_read_report()
        complete_with_limit["knowledge_limits"] = ["scan_incomplete"]

        for name, report in (
            ("partial_without_limit", partial_without_limit),
            ("unknown_with_total", unknown_with_total),
            ("complete_with_limit", complete_with_limit),
        ):
            with self.subTest(case=name):
                self.assertNotEqual(list(validator.iter_errors(report)), [])

    def test_complete_report_rejects_count_total_mismatch(self) -> None:
        self.assertTrue(VALIDATOR.is_file(), "semantic row diagnostics validator is required")
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["counts"] = {"shapefile.inner_ring_without_outer": 1}

        with self.assertRaisesRegex(ValueError, "counts sum"):
            module.validate_report(report)

    def test_examples_must_respect_declared_limit(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["examples_limit"] = 1
        report["examples_truncated"] = True

        with self.assertRaisesRegex(ValueError, "examples exceed examples_limit"):
            module.validate_report(report)

    def test_truncation_flag_must_match_observed_examples(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["examples_limit"] = 1
        report["examples"] = report["examples"][:1]

        with self.assertRaisesRegex(ValueError, "examples_truncated"):
            module.validate_report(report)

        report["examples_truncated"] = True
        module.validate_report(report)

    def test_truncation_true_requires_the_example_limit_to_omit_rows(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["examples_truncated"] = True

        with self.assertRaisesRegex(ValueError, "only when examples_limit"):
            module.validate_report(report)

    def test_write_report_requires_outcome_partition(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = partial_write_report()
        report.pop("write_outcome")

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(errors, [], "write_outcome must be required for write scope")

    def test_write_report_requires_diagnostic_state_partition(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = partial_write_report()
        report.pop("diagnostic_state_counts")

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(
            errors,
            [],
            "diagnostic_state_counts must be required for write scope",
        )

    def test_write_report_models_rolled_back_attempts_and_input_total(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = partial_write_report()

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertEqual(errors, [])

    def test_all_known_partition_and_rolled_back_example_are_valid(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = rolled_back_write_report()
        report["counts"] = {"transaction.rolled_back_due_to_peer": 1}
        report["diagnostic_state_counts"] = {
            "certainly_rejected": 0,
            "certainly_not_attempted": 0,
            "certainly_rolled_back": 1,
            "effect_unknown": 0,
        }
        report["examples"][0]["cause"] = "transaction.rolled_back_due_to_peer"
        report["examples"][0]["write_state"] = "certainly_rolled_back"

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertEqual(errors, [])

        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate_report(report)

    def test_read_report_forbids_write_only_fields(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()
        report["input_total"] = 2

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(errors, [], "input_total is meaningful only for writes")

    def test_read_examples_forbid_write_state(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()
        report["examples"][0]["write_state"] = "certainly_rejected"

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(errors, [], "write_state is meaningful only for writes")

    def test_read_report_forbids_diagnostic_state_partition(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()
        report["diagnostic_state_counts"] = {
            "certainly_rejected": 2,
            "certainly_not_attempted": 0,
            "certainly_rolled_back": 0,
            "effect_unknown": 0,
        }

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(errors, [], "diagnostic states are meaningful only for writes")

    def test_known_write_partition_must_sum_to_input_total(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = rolled_back_write_report()
        report["write_outcome"]["certainly_rolled_back"]["value"] = 4_998

        with self.assertRaisesRegex(ValueError, "write outcome sum"):
            module.validate_report(report)

    def test_known_write_buckets_cannot_exceed_input_total(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = partial_write_report()
        report["write_outcome"]["certainly_not_attempted"]["value"] = 6_000

        with self.assertRaisesRegex(ValueError, "known write outcome sum"):
            module.validate_report(report)

    def test_known_buckets_plus_diagnosed_unknown_rows_fit_input_total(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = partial_write_report()
        report["write_outcome"]["certainly_not_attempted"]["value"] = 5_199
        report["diagnostic_state_counts"]["certainly_rejected"] = 0
        report["diagnostic_state_counts"]["certainly_rolled_back"] = 1
        report["examples"][0]["write_state"] = "certainly_rolled_back"

        with self.assertRaisesRegex(ValueError, "known outcomes plus diagnosed unknown"):
            module.validate_report(report)

    def test_unsafe_numeric_key_requires_canonical_string_encoding(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = complete_read_report()
        report["examples"][0]["key"] = {
            "field": "ID_PART",
            "state": "value",
            "value": 9_007_199_254_741_009,
        }

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(errors, [], "unsafe numeric keys must use decimal strings")

    def test_write_observed_total_cannot_exceed_input_total(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = rolled_back_write_report()
        report["observed_total"] = 5_201
        report["total"] = 5_201
        report["counts"] = {"mysql.constraint_violation": 5_201}
        report["examples_truncated"] = False
        report["write_outcome"]["certainly_rejected"]["value"] = 5_201
        report["write_outcome"]["certainly_rolled_back"]["value"] = 0
        report["write_outcome"]["certainly_not_attempted"]["value"] = 0

        with self.assertRaisesRegex(ValueError, "observed_total exceeds input_total"):
            module.validate_report(report)

    def test_diagnostic_state_count_cannot_exceed_known_outcome_bucket(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = rolled_back_write_report()
        report["observed_total"] = 2
        report["total"] = 2
        report["counts"] = {"mysql.constraint_violation": 2}
        report["diagnostic_state_counts"]["certainly_rejected"] = 2
        second_example = deepcopy(report["examples"][0])
        second_example["source_index"] = 5_000
        report["examples"].append(second_example)
        with self.assertRaisesRegex(ValueError, "exceeds known write outcome bucket"):
            module.validate_report(report)

    def test_diagnostic_state_counts_must_sum_to_observed_total(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = partial_write_report()
        report["diagnostic_state_counts"]["certainly_rejected"] = 2

        with self.assertRaisesRegex(ValueError, "diagnostic state sum"):
            module.validate_report(report)

    def test_write_examples_require_explicit_state(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        report = partial_write_report()
        report["examples"][0].pop("write_state")

        errors = list(Draft202012Validator(schema).iter_errors(report))
        self.assertNotEqual(errors, [], "write examples must classify their known state")

    def test_example_cause_must_exist_in_counts(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["examples"][0]["cause"] = "shapefile.other"

        with self.assertRaisesRegex(ValueError, "cause absent from counts"):
            module.validate_report(report)

    def test_examples_cannot_exceed_observed_or_per_cause_counts(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        too_many_rows = complete_read_report()
        duplicate = deepcopy(too_many_rows["examples"][0])
        duplicate["source_index"] = 99
        too_many_rows["examples"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "examples exceed observed_total"):
            module.validate_report(too_many_rows)

        too_many_for_cause = complete_read_report()
        too_many_for_cause["examples"][1]["cause"] = (
            "shapefile.inner_ring_without_outer"
        )
        with self.assertRaisesRegex(ValueError, "examples exceed count for cause"):
            module.validate_report(too_many_for_cause)

    def test_example_source_indices_must_be_unique(self) -> None:
        spec = importlib.util.spec_from_file_location("row_diagnostics", VALIDATOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = complete_read_report()
        report["examples"][1]["source_index"] = report["examples"][0]["source_index"]

        with self.assertRaisesRegex(ValueError, "duplicate source_index"):
            module.validate_report(report)

    def test_icd_and_capability_manifest_bind_row_diagnostics_schema(self) -> None:
        icd = ICD.read_text(encoding="utf-8")
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))

        self.assertIn("versione 2.0-rc17", icd)
        self.assertIn("§9.9–§9.14", icd)
        for rule in range(9, 15):
            self.assertIn(f"**R9.{rule}**", icd)
        capability = components["required_row_diagnostics"]
        self.assertEqual(capability["schema"], "conformance/schemas/row-diagnostics-v1.schema.json")
        self.assertEqual(capability["rule_state"], "proposta")


if __name__ == "__main__":
    unittest.main()
