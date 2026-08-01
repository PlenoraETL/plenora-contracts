from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "conformance" / "campaigns" / "v1.0.0" / "components.json"
EXECUTION_MANIFEST = (
    ROOT / "conformance" / "campaigns" / "v1.0.0" / "execution.json"
)
LIVE_SPEC = ROOT / "conformance" / "campaigns" / "v1.0.0" / "live-postgres.json"
LIVE_EVIDENCE = (
    ROOT
    / "conformance"
    / "campaigns"
    / "v1.0.0"
    / "evidence"
    / "qualified"
    / "2026-08-01-live-postgres-data-io.json"
)
CROSS_SPEC = (
    ROOT / "conformance" / "campaigns" / "v1.0.0" / "plenora-read-only.json"
)
CROSS_EVIDENCE = (
    ROOT
    / "conformance"
    / "campaigns"
    / "v1.0.0"
    / "evidence"
    / "qualified"
    / "2026-08-01-plenora-read-only.json"
)
PROVENANCE = (
    ROOT
    / "conformance"
    / "campaigns"
    / "v1.0.0"
    / "evidence"
    / "qualified"
    / "2026-08-01-provenance.json"
)

EXPECTED_REVISIONS = {
    "plenora-data-tools": "aab8152902a209955b2ea657dfeaeea10408f866",
    "plenora-IO-tools": "ca7f34c6b732700fa79f579f7b003df27ce54b09",
    "plenora-database-tools": "89c82c4c700550decc394bb1e43b22c8a32e44e1",
}


class CampaignManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.execution = json.loads(EXECUTION_MANIFEST.read_text(encoding="utf-8"))
        cls.live_spec = json.loads(LIVE_SPEC.read_text(encoding="utf-8"))
        cls.live_evidence = json.loads(LIVE_EVIDENCE.read_text(encoding="utf-8"))
        cls.cross_spec = json.loads(CROSS_SPEC.read_text(encoding="utf-8"))
        cls.cross_evidence = json.loads(CROSS_EVIDENCE.read_text(encoding="utf-8"))
        cls.provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))

    def test_qualified_report_hashes_match_provenance(self) -> None:
        self.assertEqual(self.provenance["hash_basis"], "canonical_lf")

        def canonical_sha256(path: Path) -> str:
            return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

        self.assertEqual(
            set(self.provenance["runner_snapshot"]),
            {
                "conformance/campaigns/v1.0.0/execution.json",
                "conformance/corpus/generate.py",
                "conformance/run-in-container.sh",
                "conformance/run_roundtrip.py",
                "conformance/run_chain.py",
                "conformance/run_pairwise.py",
                "conformance/_shared.py",
                "conformance/comparator.py",
                "conformance/fidelity.py",
            },
        )
        for relative, expected_hash in self.provenance["runner_snapshot"].items():
            with self.subTest(relative=relative):
                self.assertEqual(canonical_sha256(ROOT / relative), expected_hash)
        evidence_root = PROVENANCE.parent
        for name, report in self.provenance["reports"].items():
            with self.subTest(name=name):
                self.assertEqual(canonical_sha256(evidence_root / name), report["sha256"])

    def test_execution_state_records_passed_format_gates_and_blocking_gap(self) -> None:
        qualification = self.execution["qualification"]
        self.assertEqual(qualification["state"], "partial_pass_with_blocking_gaps")
        self.assertEqual(qualification["isolated_roundtrips"], "passed_90_of_90")
        self.assertEqual(qualification["io_data_pairwise"], "passed_30_of_30")
        self.assertEqual(
            qualification["persistent_reverse_roundtrip"],
            "incomplete_blocking",
        )

    def test_pins_exact_three_v1_release_revisions(self) -> None:
        observed = {
            component["name"]: component["revision"]
            for component in self.manifest["components"]
        }
        self.assertEqual(observed, EXPECTED_REVISIONS)
        observed_tags = {
            component["name"]: component["tag"]
            for component in self.manifest["components"]
        }
        self.assertEqual(
            observed_tags,
            {
                "plenora-data-tools": "v1.0.1",
                "plenora-IO-tools": "v1.0.0",
                "plenora-database-tools": "v1.0.0",
            },
        )
        self.assertEqual(
            self.manifest["release_inventory"],
            "conformance/releases/v1.0.1.json",
        )

    def test_execution_manifest_uses_the_same_immutable_pins(self) -> None:
        campaign = {
            row["name"]: (row["tag"], row["revision"])
            for row in self.manifest["components"]
        }
        execution = {
            row["name"]: (row["tag"], row["revision"])
            for row in self.execution["components"]
        }
        self.assertEqual(execution, campaign)
        self.assertEqual(
            [row["id"] for row in self.execution["roundtrips"]],
            ["io", "data", "database"],
        )
        self.assertTrue(
            all(row["status"] == "available" for row in self.execution["roundtrips"])
        )

    def test_live_postgres_chain_is_exact_and_does_not_overclaim_persistence(self) -> None:
        self.assertEqual(self.live_evidence["status"], "pass")
        self.assertEqual(self.live_evidence["database_export"]["determinism"], "byte_exact")
        self.assertEqual(
            self.live_evidence["database_export"]["source_rows_observed_after_export"],
            3,
        )
        self.assertNotIn("durability", self.live_evidence["database_export"])
        self.assertEqual(self.live_evidence["database_to_data"]["status"], "pass")
        self.assertEqual(self.live_evidence["data_to_io"]["values"], "pass")
        self.assertEqual(self.live_evidence["data_to_io"]["transition_judge"], "pass")
        self.assertEqual(len(self.live_spec["required_transitions"]), 2)
        self.assertEqual(
            self.live_evidence["persistent_database_roundtrip"], "not_demonstrated"
        )
        self.assertEqual(
            self.live_evidence["providers_not_exercised"], ["mysql", "sqlserver"]
        )

    def test_binding_and_proposal_profiles_are_separate(self) -> None:
        profiles = self.manifest["profiles"]
        self.assertEqual(profiles["binding-v1"]["rule_state"], "ratificata")
        self.assertEqual(profiles["target-rc16"]["rule_state"], "proposta")
        self.assertFalse(profiles["target-rc16"]["binding_claim"])

    def test_plenora_comparison_is_exact_read_only_and_scoped(self) -> None:
        self.assertEqual(
            self.cross_evidence["status"], "pass_with_declared_differences"
        )
        self.assertEqual(
            self.cross_evidence["reference_revisions"],
            {
                "plenora": "fff9619bfdad6605afcaeabbeff5126f0282e72c",
                "data": "aab8152902a209955b2ea657dfeaeea10408f866",
            },
        )
        self.assertEqual(self.cross_evidence["filter"]["logical_values"], "pass")
        self.assertEqual(
            self.cross_evidence["filter"]["undeclared_contract_differences"], []
        )
        self.assertLessEqual(
            self.cross_evidence["reproject"]["max_hausdorff_degrees"],
            self.cross_spec["reproject"]["hausdorff_tolerance_degrees"],
        )
        encoded = json.dumps(self.cross_evidence["scope_limits"])
        self.assertIn("read-only", encoded)
        self.assertIn("does not establish persistence", encoded)

    def test_io_reader_and_writer_loss_are_declared_available(self) -> None:
        io = next(
            component
            for component in self.manifest["components"]
            if component["name"] == "plenora-IO-tools"
        )
        self.assertEqual(io["capabilities"]["read_loss"], "available")
        self.assertEqual(io["capabilities"]["write_loss"], "available")

    def test_only_postgres_has_v1_live_ipc_export(self) -> None:
        exports = self.manifest["database_exports"]
        self.assertEqual(exports["postgres"]["status"], "available")
        self.assertEqual(exports["postgres"]["command"], "postgres-read-ipc")
        for provider in ("sqlserver", "mysql"):
            self.assertEqual(exports[provider]["status"], "incomplete_blocking")
            self.assertIsNone(exports[provider]["command"])

    def test_reverse_persistence_is_explicitly_incomplete(self) -> None:
        reverse = self.manifest["directions"]["io_to_data_to_database"]
        self.assertEqual(reverse["status"], "incomplete_blocking")
        self.assertEqual(reverse["terminal_coverage"], "contract_observer_only")
        self.assertFalse(reverse["satisfies_system_gate"])

    def test_published_data_release_remediation_is_machine_readable(self) -> None:
        blocker = self.manifest["known_blockers"]["data_bound_crs_towgs84"]
        self.assertEqual(blocker["component"], "plenora-data-tools")
        self.assertEqual(blocker["tag"], "v1.0.0")
        self.assertEqual(
            blocker["revision"],
            "7a47504482569636b6c0e268477d155010d3b030",
        )
        self.assertEqual(blocker["fixture"], "crs_wkt_towgs84")
        self.assertEqual(blocker["status"], "remediated_by_patch_release")
        self.assertIn("BoundCRS", blocker["observed_error"])
        self.assertEqual(blocker["remediation_tag"], "v1.0.1")
        self.assertEqual(
            blocker["remediation_revision"],
            "aab8152902a209955b2ea657dfeaeea10408f866",
        )
        self.assertTrue(blocker["remediation_functional_qualification_valid"])
        self.assertFalse(blocker["blocks_system_gate"])
        self.assertEqual(
            self.manifest["execution"]["system_gate"],
            "partial_pass_with_blocking_gaps",
        )

    def test_mysql_write_is_forbidden_not_skipped(self) -> None:
        mysql = self.manifest["database_writes"]["mysql"]
        self.assertEqual(mysql["status"], "expected_rejection")
        self.assertEqual(mysql["remote_effect"], "none")
        self.assertTrue(mysql["successful_write_is_failure"])

    def test_no_skip_state_exists_in_required_matrix(self) -> None:
        encoded = json.dumps(self.manifest, sort_keys=True)
        self.assertNotIn('"skipped"', encoded)
        self.assertNotIn('"skip"', encoded)


if __name__ == "__main__":
    unittest.main()
