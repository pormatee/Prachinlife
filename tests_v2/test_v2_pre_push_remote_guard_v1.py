import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "pre_push_remote_guard_v1.py"

spec = importlib.util.spec_from_file_location("pre_push_remote_guard_v1", MODULE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


class TestPrePushRemoteGuardV1(unittest.TestCase):
    def snapshot(self):
        return {
            "schema_version": m.SCHEMA_VERSION,
            "branch": "main",
            "local_head": "local-a",
            "remote_head": "remote-a",
            "ahead": 4,
            "behind": 0,
            "tracked_clean": True,
        }

    def current(self):
        return {
            "branch": "main",
            "local_head": "local-a",
            "remote_head": "remote-a",
            "ahead": 4,
            "behind": 0,
            "tracked_clean": True,
        }

    def test_01_validated_state_is_ready(self):
        self.assertEqual([], m.evaluate_pre_push(self.snapshot(), self.current()))

    def test_02_remote_move_blocks_push(self):
        c = self.current()
        c["remote_head"] = "remote-b"
        self.assertIn("REMOTE_MOVED_AFTER_VALIDATION", m.evaluate_pre_push(self.snapshot(), c))

    def test_03_local_head_change_blocks_push(self):
        c = self.current()
        c["local_head"] = "local-b"
        self.assertIn("LOCAL_HEAD_CHANGED_AFTER_VALIDATION", m.evaluate_pre_push(self.snapshot(), c))

    def test_04_behind_remote_blocks_push(self):
        c = self.current()
        c["behind"] = 1
        self.assertIn("LOCAL_BEHIND_REMOTE", m.evaluate_pre_push(self.snapshot(), c))

    def test_05_dirty_tracked_worktree_blocks_push(self):
        c = self.current()
        c["tracked_clean"] = False
        self.assertIn("TRACKED_WORKTREE_NOT_CLEAN", m.evaluate_pre_push(self.snapshot(), c))

    def test_06_no_local_commits_blocks_push(self):
        c = self.current()
        c["ahead"] = 0
        self.assertIn("NO_LOCAL_COMMITS_TO_PUSH", m.evaluate_pre_push(self.snapshot(), c))

    def test_07_wrong_branch_blocks_push(self):
        c = self.current()
        c["branch"] = "feature"
        self.assertIn("WRONG_BRANCH", m.evaluate_pre_push(self.snapshot(), c))

    def test_08_tool_has_no_push_action(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn('choices=("record", "check", "push")', source)
        self.assertIn("PUSH_EXECUTED=FALSE", source)


if __name__ == "__main__":
    unittest.main()
