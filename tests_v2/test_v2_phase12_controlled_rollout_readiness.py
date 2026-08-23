from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.phase12_controlled_rollout_readiness import (
    FILES,
    assert_post_switch,
    staged_public_diff,
)

class Phase12ControlledRolloutReadinessTest(unittest.TestCase):
    def _tree(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        stage = root / "data/v2/staging/user_web"
        stage.mkdir(parents=True)
        for i, name in enumerate(FILES):
            (root / name).write_text(json.dumps([{"id": f"old-{i}"}]), encoding="utf-8")
            (stage / name).write_text(json.dumps([{"id": f"new-{i}"}]), encoding="utf-8")
        return td, root, stage

    def test_1201_exact_file_set(self):
        self.assertEqual(len(FILES), 4)
        self.assertIn("prachinlife_index.json", FILES)
        self.assertIn("vegetarian_index.json", FILES)
        self.assertIn("go_index.json", FILES)
        self.assertIn("service_index.json", FILES)

    def test_1202_diff_detects_changes(self):
        td, root, stage = self._tree()
        with td:
            d = staged_public_diff(root, stage)
            self.assertTrue(all(x["will_change"] for x in d.values()))

    def test_1203_post_switch_accepts_byte_match(self):
        td, root, stage = self._tree()
        with td:
            for name in FILES:
                (root / name).write_bytes((stage / name).read_bytes())
            self.assertEqual(assert_post_switch(root, stage)["status"], "PASS")

    def test_1204_post_switch_rejects_mismatch(self):
        td, root, stage = self._tree()
        with td:
            with self.assertRaises(RuntimeError):
                assert_post_switch(root, stage)

    def test_1205_json_array_required(self):
        td, root, stage = self._tree()
        with td:
            for name in FILES:
                (root / name).write_bytes((stage / name).read_bytes())
            bad = FILES[0]
            (root / bad).write_text('{"bad": true}', encoding="utf-8")
            (stage / bad).write_text('{"bad": true}', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                assert_post_switch(root, stage)

    def test_1206_missing_file_fail_closed(self):
        td, root, stage = self._tree()
        with td:
            for name in FILES:
                (root / name).write_bytes((stage / name).read_bytes())
            (stage / FILES[1]).unlink()
            with self.assertRaises(RuntimeError):
                assert_post_switch(root, stage)

if __name__ == "__main__":
    unittest.main()
