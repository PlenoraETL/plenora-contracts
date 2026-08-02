from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "contract-assurance.yml"
CONTAINER_RUNNER = ROOT / "conformance" / "run-in-container.sh"


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_candidate_sha_is_checked_out_and_verified(self) -> None:
        self.assertIn("CANDIDATE_SHA:", self.text)
        self.assertIn("github.event.pull_request.head.sha", self.text)
        self.assertIn("ref: ${{ env.CANDIDATE_SHA }}", self.text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$CANDIDATE_SHA"', self.text)

    def test_pinned_pyarrow_test_environment_runs_all_conformance_tests(self) -> None:
        self.assertIn("pyarrow==23.0.1", self.text)
        normalized = " ".join(self.text.split())
        self.assertIn("unittest discover -s conformance/tests", normalized)

    def test_live_release_gate_has_token_and_preserved_report(self) -> None:
        self.assertIn("conformance/verify_release_inputs.py", self.text)
        self.assertIn("conformance/releases/v1.0.0.json", self.text)
        self.assertIn("conformance/releases/v1.0.1.json", self.text)
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.text)
        self.assertIn("assurance-results/release-inputs-v1.0.0.json", self.text)
        self.assertIn("assurance-results/release-inputs-v1.0.1.json", self.text)

    def test_container_runner_recreates_corpus_directory(self) -> None:
        runner = CONTAINER_RUNNER.read_text(encoding="utf-8")
        self.assertIn('cases_real=$(realpath -m -- "${CASES}")', runner)
        self.assertIn('"${root_real}/cases"', runner)
        self.assertIn('"${contracts_real}/conformance/cases"', runner)
        self.assertIn('rm -rf -- "${cases_real}"', runner)
        self.assertIn('mkdir -p "${cases_real}"', runner)
        self.assertNotIn('rm -rf -- "${CASES}"', runner)

    def test_container_runner_defaults_to_qualified_execution_manifest(self) -> None:
        runner = CONTAINER_RUNNER.read_text(encoding="utf-8")

        self.assertIn(
            'MANIFEST=${MANIFEST:-"${CONTRACTS}/conformance/campaigns/v1.0.0/execution.json"}',
            runner,
        )

    def test_container_runner_executes_and_preserves_pairwise_report(self) -> None:
        runner = CONTAINER_RUNNER.read_text(encoding="utf-8")
        self.assertIn("conformance/run_pairwise.py", runner)
        self.assertIn('${REPORT%.json}-pairwise.json', runner)
        self.assertIn("[ ${pairwise} -ne 0 ]", runner)

    def test_workflow_regenerates_retained_artifact_evidence(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for dependency in (
            "pyarrow==23.0.1",
            "tzdata==2025.3",
            "shapely==2.1.2",
            "PyYAML==6.0.3",
            "jsonschema==4.26.0",
        ):
            self.assertIn(dependency, workflow)
        self.assertIn("conformance/judge_live_postgres.py", workflow)
        self.assertIn("conformance/judge_plenora_cross.py", workflow)
        self.assertGreaterEqual(workflow.count("cmp "), 2)


if __name__ == "__main__":
    unittest.main()
