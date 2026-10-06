"""The pip-audit job audits every variant of the hashed locks.

pip-audit evaluates environment markers on the interpreter it runs on: a lock
line whose marker is false there (`rpds-py==0.30.0 ; python_full_version <
'3.11'` under Python 3.12) is skipped without a word, although the validate
job installs it. The audit matrix must therefore contain, for every
supported Python, a version that selects the same lock lines.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
LOCKS = sorted(ROOT.glob("requirements-*.txt"))

COMPARISON = re.compile(r"^python_full_version\s*(<=|>=|<|>|==|!=)\s*'(\d+)\.(\d+)'$")


def version(text):
    major, minor = text.split(".")
    return (int(major), int(minor))


def job_matrix(workflow, job):
    """The `python` list of one job's matrix, read from the workflow text."""
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    block = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  [A-Za-z_-]+:\n|\Z)", text, re.M | re.S)
    if block is None:
        raise AssertionError(f"{workflow} has no job {job}")
    found = re.search(r"^\s+python:\s*\[([^\]]*)\]", block.group(1), re.M)
    if found is None:
        raise AssertionError(f"{workflow} job {job} has no python matrix")
    return [version(item.strip().strip("'\"")) for item in found.group(1).split(",")]


def marker_holds(marker, python):
    """Evaluate the markers the locks use; any other marker is refused, so a
    platform marker cannot pass this check unexamined."""
    result = True
    for clause in marker.split(" and "):
        match = COMPARISON.match(clause.strip())
        if match is None:
            raise AssertionError(f"unsupported lock marker: {clause.strip()}")
        operator, bound = match.group(1), (int(match.group(2)), int(match.group(3)))
        result = result and {
            "<": python < bound, "<=": python <= bound, ">": python > bound,
            ">=": python >= bound, "==": python == bound, "!=": python != bound,
        }[operator]
    return result


def lock_variant(python, locks=LOCKS):
    """The lock lines a given Python installs."""
    selected = []
    for lock in locks:
        for line in lock.read_text(encoding="utf-8").splitlines():
            if not line or line[0] in " #-":
                continue
            requirement = line.rstrip(" \\")
            name, _, marker = requirement.partition(" ; ")
            if not marker or marker_holds(marker, python):
                selected.append((lock.name, name.strip()))
    return tuple(selected)


def unaudited_variants(supported, audited, locks=LOCKS):
    audited_variants = {lock_variant(python, locks) for python in audited}
    return [
        python for python in supported
        if lock_variant(python, locks) not in audited_variants
    ]


class AuditMatrixTests(unittest.TestCase):
    def test_every_lock_variant_is_audited(self):
        validated = job_matrix("spec-validation.yml", "validate")
        low, high = min(validated), max(validated)
        supported = [(low[0], minor) for minor in range(low[1], high[1] + 1)]
        audited = job_matrix("supply-chain.yml", "pip-audit")
        self.assertEqual(unaudited_variants(supported, audited), [])

    def test_a_single_interpreter_misses_the_old_python_variant(self):
        missing = unaudited_variants([(3, 10), (3, 12), (3, 14)], [(3, 12)])
        self.assertIn((3, 10), missing)
        self.assertIn((3, 14), missing)

    def test_platform_marker_is_refused(self):
        with self.assertRaises(AssertionError):
            marker_holds("sys_platform == 'win32'", (3, 12))


if __name__ == "__main__":
    unittest.main()
