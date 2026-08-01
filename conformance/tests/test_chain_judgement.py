from __future__ import annotations

import inspect
import unittest

from conformance import run_chain


class ChainJudgementTests(unittest.TestCase):
    def test_chain_uses_structured_ipc_judgement_per_stage(self) -> None:
        source = inspect.getsource(run_chain.main)

        self.assertIn("judge_ipc_transition(", source)
        self.assertIn('"semantic_error"', source)
        self.assertNotIn("judge_transition(", source)

    def test_semantic_stage_error_blocks_terminal_observer(self) -> None:
        source = inspect.getsource(run_chain.main)

        self.assertIn('s["outcome"] in {"error", "semantic_error"}', source)
        self.assertIn("if not semantic_ok:", source)


if __name__ == "__main__":
    unittest.main()
