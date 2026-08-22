import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestIdentityRolloutRunner(unittest.TestCase):
    def test_runner_exists_and_is_safety_scoped(self):
        text = (ROOT / "scripts/run_identity_anchor_rollout.py").read_text(encoding="utf-8")
        self.assertIn("select_identity_anchor_queue", text)
        self.assertIn("commit_current_observations", text)
        self.assertIn("--commit-observations", text)
        self.assertIn('"production_json_changed": False', text)
        self.assertIn('"canonical_fields_changed": False', text)


if __name__ == "__main__":
    unittest.main()
