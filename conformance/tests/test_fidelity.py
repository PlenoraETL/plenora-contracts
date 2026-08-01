from __future__ import annotations

import unittest

from conformance.fidelity import (
    judge_allowed_transitions,
    judge_loss_counts,
    judge_transitions,
)


class FidelityJudgeTests(unittest.TestCase):
    def test_no_loss_and_no_report_passes(self) -> None:
        report = judge_loss_counts({}, {}, {})
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issues"], [])

    def test_exact_expected_observed_and_reported_loss_passes(self) -> None:
        counts = {"identifier_truncation": 2, "unsupported_dimension": 1}
        report = judge_loss_counts(counts, counts, counts)
        self.assertEqual(report["status"], "pass")

    def test_observed_loss_without_report_is_unreported(self) -> None:
        report = judge_loss_counts(
            {"identifier_truncation": 1},
            {"identifier_truncation": 1},
            {},
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(issue["kind"] == "unreported_loss" for issue in report["issues"])
        )

    def test_report_without_observed_loss_is_spurious(self) -> None:
        report = judge_loss_counts({}, {}, {"identifier_truncation": 1})
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(issue["kind"] == "spurious_loss" for issue in report["issues"])
        )

    def test_observed_loss_not_authorized_by_fixture_is_forbidden(self) -> None:
        report = judge_loss_counts({}, {"precision_loss": 1}, {"precision_loss": 1})
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(issue["kind"] == "forbidden_loss" for issue in report["issues"])
        )

    def test_expected_loss_that_did_not_happen_is_a_fixture_or_component_mismatch(self) -> None:
        report = judge_loss_counts(
            {"identifier_truncation": 1},
            {},
            {},
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(issue["kind"] == "expected_loss_missing" for issue in report["issues"])
        )

    def test_counts_must_be_nonnegative_integers(self) -> None:
        for invalid in (-1, 1.5, True, "1"):
            with self.subTest(invalid=invalid):
                report = judge_loss_counts(
                    {"identifier_truncation": invalid},
                    {},
                    {},
                )
                self.assertEqual(report["status"], "harness_error")


class TransitionJudgeTests(unittest.TestCase):
    def test_allowed_transition_is_optional_but_fail_closed(self) -> None:
        allowed = [
            {
                "category": "contract",
                "path": "plenora.geometry.srid",
                "before": None,
                "after": "4326",
                "reason": "authority_derived_srid_completion",
            }
        ]
        self.assertEqual(judge_allowed_transitions(allowed, [])["status"], "pass")
        unexpected = [
            {
                "category": "contract",
                "path": "plenora.geometry.srid",
                "before": None,
                "after": "3003",
            }
        ]
        verdict = judge_allowed_transitions(allowed, unexpected)
        self.assertEqual(verdict["status"], "fail")
        self.assertEqual(verdict["issues"][0]["kind"], "forbidden_transition")

    EXPECTED = [
        {
            "category": "contract",
            "path": "fields[0].metadata['plenora.geometry.srid']",
            "before": None,
            "after": "3003",
            "reason": "authority_derived_srid_completion",
        }
    ]
    OBSERVED = [
        {
            "category": "contract",
            "path": "fields[0].metadata['plenora.geometry.srid']",
            "before": None,
            "after": "3003",
        }
    ]

    def test_exact_allowed_transition_passes(self) -> None:
        report = judge_transitions(self.EXPECTED, self.OBSERVED)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issues"], [])

    def test_unexpected_transition_is_forbidden(self) -> None:
        report = judge_transitions([], self.OBSERVED)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["issues"][0]["kind"], "forbidden_transition")

    def test_expected_transition_that_did_not_happen_fails(self) -> None:
        report = judge_transitions(self.EXPECTED, [])
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["issues"][0]["kind"], "expected_transition_missing")

    def test_expected_transition_requires_a_reason(self) -> None:
        report = judge_transitions(
            [{key: value for key, value in self.EXPECTED[0].items() if key != "reason"}],
            self.OBSERVED,
        )
        self.assertEqual(report["status"], "harness_error")


if __name__ == "__main__":
    unittest.main()
