"""The summary line of the complete gate counts what it checked: a figure
written as a literal would stay right only by accident."""

import contextlib
import io
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_specs as validator


def summary(root=None, **patches):
    root = root or validator.ROOT
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(validator, "ROOT", root))
        stack.enter_context(patch.object(validator, "SCHEMA_DIR", root / "schemas"))
        for name, value in patches.items():
            stack.enter_context(patch.object(validator, name, value))
        output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        errors = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        status = validator.main()
    if status != 0:
        raise AssertionError(errors.getvalue())
    return output.getvalue()


def figure(text, label):
    match = re.search(rf"(\d+) {label}", text)
    if match is None:
        raise AssertionError(f"no figure for {label} in {text!r}")
    return int(match.group(1))


class SummaryCountTests(unittest.TestCase):
    def test_error_bound_probes_are_counted(self):
        base = figure(summary(), "semantic error-bound probes")
        self.assertEqual(
            base, len(validator.ERROR_BOUND_PROBES) + sum(validator.ERROR_BOUND_CASES.values())
        )
        extra = dict(validator.ERROR_BOUND_PROBES)
        extra["second string byte limit"] = (
            {"other": "y" * (validator.MAX_ERROR_DETAILS_STRING_BYTES + 1)},
            "string exceeds the byte limit",
        )
        self.assertEqual(
            figure(summary(ERROR_BOUND_PROBES=extra), "semantic error-bound probes"), base + 1
        )

    def test_binding_maps_are_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for entry in validator.ROOT.iterdir():
                if entry.name in {".git", "__pycache__"}:
                    continue
                if entry.is_dir():
                    shutil.copytree(entry, root / entry.name, ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    shutil.copy2(entry, root / entry.name)
            self.assertEqual(figure(summary(root), "binding maps"), 3)
            shutil.copy2(root / "bindings/cli-v1.json", root / "bindings/cli-copy-v1.json")
            # The inventory guard would stop the run; only the count is probed.
            text = summary(root, validate_bindings=lambda catalogs: [])
            self.assertEqual(figure(text, "binding maps"), 4)


if __name__ == "__main__":
    unittest.main()
