import unittest
from pathlib import Path


class TestResumableRolloutRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path("scripts/run_identity_anchor_rollout.py").read_text(encoding="utf-8")

    def test_runner_has_timeout_control(self):
        self.assertIn('--timeout', self.text)
        self.assertIn('timeout=timeout', self.text)

    def test_runner_has_progress_output(self):
        self.assertIn('[{index}/{len(queue)}]', self.text)

    def test_runner_commits_incrementally(self):
        self.assertIn('CHECKPOINT COMMIT', self.text)
        self.assertIn('--batch-size', self.text)

    def test_commit_alias_is_supported(self):
        self.assertIn('"--commit-observations", "--commit"', self.text)

    def test_runner_declares_resumable_report(self):
        self.assertIn('"resumable": True', self.text)


if __name__ == '__main__':
    unittest.main()
