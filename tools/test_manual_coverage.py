"""Manual coverage measures a fixed revision without weakening PR checks."""

import contextlib
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import yaml

import check_schema_immutability as gate
import ci_locale
import run_gate_tests

ROOT = Path(__file__).resolve().parents[1]


class SnapshotTests(unittest.TestCase):
    def run_snapshot(self, revision, event="workflow_dispatch", errors=()):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": event}), \
                patch("sys.argv", ["check", "--measured-commit", revision]), \
                patch.object(gate, "git", return_value="a" * 40) as git, \
                patch.object(gate, "check", return_value=list(errors)) as check, \
                patch.object(gate, "stale_main_error", side_effect=AssertionError("moving main")), \
                patch.object(gate, "fork_point", side_effect=AssertionError("moving main")), \
                contextlib.redirect_stdout(io.StringIO()):
            result = gate.main()
        return result, git, check

    def test_snapshot_does_not_read_moving_main_and_keeps_floor(self):
        status, git, check = self.run_snapshot("a" * 40)
        self.assertEqual(status, 0)
        git.assert_called_once_with(gate.ROOT, "rev-parse", "HEAD^{commit}")
        self.assertEqual([call.args[1] for call in check.call_args_list], [gate.RATIFIED_BASE, "a" * 40])

    def test_wrong_revision_and_automatic_events_fail_closed(self):
        for revision, event in (("b" * 40, "workflow_dispatch"), ("HEAD", "workflow_dispatch"),
                                ("a" * 40, "pull_request"), ("a" * 40, "push")):
            with self.subTest(revision=revision, event=event):
                status, _, check = self.run_snapshot(revision, event)
                self.assertEqual(status, 1)
                check.assert_not_called()

    def test_snapshot_still_rejects_contract_mutation(self):
        self.assertEqual(self.run_snapshot("a" * 40, errors=["published document changed"])[0], 1)


class SelectionTests(unittest.TestCase):
    def test_local_runner_supports_only_linux_and_windows(self):
        for name in ("Linux", "Windows"):
            with patch.object(ci_locale.platform, "system", return_value=name):
                self.assertEqual(ci_locale.host_os(), name)
        with patch.object(ci_locale.platform, "system", return_value="unsupported"):
            with self.assertRaises(ci_locale.Unsupported):
                ci_locale.host_os()
        for job in ci_locale.derive()["jobs"]:
            self.assertIn(job["os"], ("Linux", "Windows"))

    def test_quick_and_campaigns_partition_complete_discovery(self):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tools"), pattern="test_*.py")
        complete = {test.id() for test in run_gate_tests.cases(suite)}
        quick = {test.id() for test in run_gate_tests.cases(run_gate_tests.select(suite, quick=True))}
        self.assertEqual(complete - quick, run_gate_tests.LONG_TESTS)
        self.assertEqual(run_gate_tests.select(suite).countTestCases(), len(complete))
        with self.assertRaises(ValueError):
            run_gate_tests.select(unittest.TestSuite(), quick=True)

    def test_manual_workflow_and_automatic_selection(self):
        path = ROOT / ".github/workflows/spec-coverage.yml"
        manual = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        self.assertEqual(set(manual["on"]), {"workflow_dispatch"})
        self.assertEqual(manual["concurrency"]["cancel-in-progress"], "false")
        commands = "\n".join(step.get("run", "") for step in manual["jobs"]["coverage"]["steps"])
        self.assertIn("git rev-parse HEAD", commands)
        self.assertIn('--measured-commit "$PLENORA_MEASURED_COMMIT"', commands)
        self.assertIn("unittest discover", commands)
        self.assertNotIn("git fetch", commands)
        for name in ("spec-validation.yml", "supply-chain.yml"):
            text = (path.parent / name).read_text(encoding="utf-8")
            self.assertIn("python tools/run_gate_tests.py --quick", text)
            self.assertNotIn("unittest discover", text)
        coverage = [job for job in ci_locale.derive()["jobs"] if job["key"] == "coverage"]
        self.assertEqual(len(coverage), 1)
        self.assertEqual(coverage[0]["profile"], "qualifica")


if __name__ == "__main__":
    unittest.main()
