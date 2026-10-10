"""The helpers of messages.py (decision 0021)."""

import unittest

import messages


class MessageHelperTests(unittest.TestCase):
    def test_structural_names_and_positions(self):
        self.assertEqual(messages.structural("phase", {"phase"}, 3), "phase")
        self.assertEqual(messages.structural("secret", {"phase"}, 3), "#3")
        self.assertEqual(messages.structural(7, {"phase"}, 1), "#1")
        self.assertEqual(messages.position(0), "#0")

    def test_differing_members(self):
        self.assertEqual(
            messages.differing_members({"phase": "a", "secret": 1}, {"phase": "b", "secret": 2}, {"phase"}),
            "phase, #1",
        )
        self.assertEqual(messages.differing_members({"a": 1}, {"a": 1}, set()), "none")
        self.assertEqual(messages.differing_members([1], {"a": 1}, set()), "the whole value")


if __name__ == "__main__":
    unittest.main()
