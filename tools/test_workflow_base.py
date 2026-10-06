"""The base of the immutability comparison in CI.

A push to a branch that merged `main` was compared with the branch's previous
tip, which predated a vector `main` had removed by decision: the gate reported
the merge as removing it (PR #6). Only a push to `main` uses the previous tip;
everything else uses the commit where it leaves `main`.
"""

import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/spec-validation.yml"


def steps_of(job):
    text = WORKFLOW.read_text(encoding="utf-8")
    block = re.search(rf"^  {job}:\n(.*?)(?=^  [A-Za-z_-]+:\n|\Z)", text, re.M | re.S)
    if block is None:
        raise AssertionError(f"no job {job}")
    return re.split(r"^      - ", block.group(1), flags=re.M)[1:]


class ComparisonBaseTests(unittest.TestCase):
    def test_no_job_reads_the_base_from_the_event(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("pull_request.base.sha", text)
        for line in text.splitlines():
            if "PLENORA_SCHEMA_BASE:" in line:
                self.fail(f"base set from an expression: {line.strip()}")

    def test_every_measuring_job_computes_the_base_first(self):
        for job, consumer in (
            ("validate", "check_schema_immutability.py"),
            ("coverage", "check_schema_immutability.py"),
        ):
            steps = steps_of(job)
            base = [i for i, step in enumerate(steps) if step.startswith("name: Base of the comparison")]
            uses = [i for i, step in enumerate(steps) if consumer in step]
            self.assertEqual(len(base), 1, job)
            self.assertTrue(uses and min(uses) > base[0], job)

    def test_previous_tip_only_for_a_push_to_main(self):
        (step,) = [s for s in steps_of("validate") if s.startswith("name: Base of the comparison")]
        self.assertIn('[ "$GITHUB_EVENT_NAME" = push ] && [ "$GITHUB_REF" = refs/heads/main ]', step)
        self.assertIn('base="$(git merge-base HEAD origin/main)"', step)


if __name__ == "__main__":
    unittest.main()
