"""The base of the immutability comparison in CI, on real Git histories.

PR #6: a push to a branch that merged `main` was compared with the branch's
previous tip, which predated a vector `main` had removed by decision. The
comparison base now depends on the event (tools/ci_comparison_base.py), and
the gate also compares what a branch changed with the current `origin/main`,
so an old branch cannot rewrite a document published after it forked.
"""

import contextlib
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_schema_immutability as immutability
import ci_comparison_base as comparison

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/spec-validation.yml"
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://schemas.plenora.dev/probe-v1.schema.json",
    "type": "object",
}


class Repository:
    def __init__(self, root: Path):
        self.root = root
        self.run("init", "--quiet", "--initial-branch", "main")

    def run(self, *arguments):
        return subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
             *arguments],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def write(self, relative, document):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8", newline="\n")

    def remove(self, relative):
        (self.root / relative).unlink()

    def commit(self, message):
        self.run("add", "-A")
        self.run("commit", "--quiet", "-m", message)
        return self.run("rev-parse", "HEAD")

    def publish_main(self):
        self.run("update-ref", "refs/remotes/origin/main", "main")


def gate(repository, floor, base):
    """The gate as CI runs it, outside CI markers, from the checked tree."""
    environment = {
        key: value for key, value in os.environ.items() if key not in immutability.CI_MARKERS
    }
    environment["PLENORA_SCHEMA_BASE"] = base
    with patch.object(immutability, "ROOT", repository.root), \
            patch.object(immutability, "RATIFIED_BASE", floor), \
            patch.dict("os.environ", environment, clear=True), patch("sys.argv", ["check"]), \
            contextlib.redirect_stdout(io.StringIO()) as output:
        status = immutability.main()
    return status, output.getvalue()


class HistoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name))
        self.repo.write("schemas/probe-v1.schema.json", SCHEMA)
        self.repo.write("vectors/set/kept.json", {"value": 1})
        self.repo.write("vectors/set/removed-by-main.json", {"value": 2})
        self.floor = self.repo.commit("floor")

    def base_for(self, event, ref, before=""):
        return comparison.comparison_base(event, ref, before, str(self.repo.root))

    def test_branch_that_merged_main_after_a_decided_removal_passes(self):
        # The case of PR #6: main removed a vector by decision after the
        # branch forked; the branch then merged main.
        self.repo.run("switch", "--quiet", "-c", "branch")
        self.repo.write("vectors/set/branch.json", {"value": 3})
        old_tip = self.repo.commit("branch work")
        self.repo.run("switch", "--quiet", "main")
        self.repo.remove("vectors/set/removed-by-main.json")
        # The ratified floor moves past a decided removal, as it did in this
        # repository; the floor is not what this test exercises.
        floor = self.repo.commit("decided removal")
        self.repo.publish_main()
        self.repo.run("switch", "--quiet", "branch")
        self.repo.run("merge", "--quiet", "--no-edit", "main")
        self.assertEqual(gate(self.repo, floor, old_tip)[0], 1, "the old base misreads the merge")
        base = self.base_for("push", "refs/heads/branch", old_tip)
        status, output = gate(self.repo, floor, base)
        self.assertEqual(status, 0, output)

    def test_old_branch_cannot_rewrite_a_document_main_published_after_it_forked(self):
        self.repo.run("switch", "--quiet", "-c", "branch")
        self.repo.run("switch", "--quiet", "main")
        self.repo.write("vectors/set/later.json", {"value": 4})
        self.repo.commit("main publishes later.json")
        self.repo.publish_main()
        self.repo.run("switch", "--quiet", "branch")
        self.repo.write("vectors/set/later.json", {"value": 5})
        self.repo.commit("branch writes the same path")
        base = self.base_for("push", "refs/heads/branch")
        status, output = gate(self.repo, self.floor, base)
        self.assertEqual(status, 1)
        self.assertIn("vectors/set/later.json", output)

    def test_old_branch_behind_main_is_not_a_removal(self):
        self.repo.run("switch", "--quiet", "-c", "branch")
        self.repo.write("vectors/set/branch.json", {"value": 3})
        self.repo.commit("branch work")
        self.repo.run("switch", "--quiet", "main")
        self.repo.write("vectors/set/later.json", {"value": 4})
        self.repo.commit("main publishes later.json")
        self.repo.publish_main()
        self.repo.run("switch", "--quiet", "branch")
        base = self.base_for("push", "refs/heads/branch")
        status, output = gate(self.repo, self.floor, base)
        self.assertEqual(status, 0, output)

    def test_forced_push_to_main_is_compared_with_the_previous_tip(self):
        self.repo.write("vectors/set/published.json", {"value": 6})
        previous = self.repo.commit("main publishes")
        self.repo.publish_main()
        self.repo.run("reset", "--quiet", "--hard", self.floor)
        self.repo.write("vectors/set/other.json", {"value": 7})
        self.repo.commit("rewritten main")
        self.repo.publish_main()
        base = self.base_for("push", "refs/heads/main", previous)
        self.assertEqual(base, previous)
        status, output = gate(self.repo, self.floor, base)
        self.assertEqual(status, 1)
        self.assertIn("vectors/set/published.json", output)

    def test_release_tag_must_point_to_a_commit_of_main(self):
        self.repo.publish_main()
        self.repo.run("tag", "-a", "v1.0.0", "-m", "release")
        self.repo.run("checkout", "--quiet", "v1.0.0")
        self.assertEqual(self.base_for("push", "refs/tags/v1.0.0"), self.floor)
        self.repo.run("switch", "--quiet", "-c", "elsewhere")
        self.repo.write("vectors/set/branch.json", {"value": 3})
        self.repo.commit("not on main")
        self.repo.run("tag", "-a", "v9.9.9", "-m", "release")
        self.repo.run("checkout", "--quiet", "v9.9.9")
        with self.assertRaises(ValueError):
            self.base_for("push", "refs/tags/v9.9.9")

    def test_push_to_main_without_a_previous_tip_fails(self):
        with self.assertRaises(ValueError):
            self.base_for("push", "refs/heads/main", "0" * 40)

    def test_pull_request_is_compared_where_it_leaves_main(self):
        self.repo.publish_main()
        self.repo.run("switch", "--quiet", "-c", "branch")
        self.repo.write("vectors/set/branch.json", {"value": 3})
        self.repo.commit("branch work")
        self.assertEqual(self.base_for("pull_request", "refs/pull/1/merge"), self.floor)


class WorkflowTests(unittest.TestCase):
    def steps_of(self, job):
        text = WORKFLOW.read_text(encoding="utf-8")
        block = re.search(rf"^  {job}:\n(.*?)(?=^  [A-Za-z_-]+:\n|\Z)", text, re.M | re.S)
        self.assertIsNotNone(block, job)
        return re.split(r"^      - ", block.group(1), flags=re.M)[1:]

    def test_no_job_reads_the_base_from_the_event_directly(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("pull_request.base.sha", text)
        self.assertNotIn("PLENORA_SCHEMA_BASE:", text)

    def test_every_measuring_job_takes_the_base_from_the_script_first(self):
        for job in ("validate", "coverage"):
            steps = self.steps_of(job)
            base = [
                i for i, step in enumerate(steps)
                if step.startswith("name: Base of the comparison")
                and "python tools/ci_comparison_base.py" in step
            ]
            uses = [i for i, step in enumerate(steps) if "check_schema_immutability.py" in step]
            self.assertEqual(len(base), 1, job)
            self.assertTrue(uses and min(uses) > base[0], job)


if __name__ == "__main__":
    unittest.main()
