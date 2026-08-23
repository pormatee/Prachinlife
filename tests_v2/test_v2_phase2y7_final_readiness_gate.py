from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.controlled_production_switch import FILES
from place_platform_v2.final_readiness_gate import audit_final_readiness

ROOT = Path(__file__).resolve().parents[1]


class TestPhase2Y7FinalReadinessGate(unittest.TestCase):
    def get(self):
        return audit_final_readiness(
            ROOT,
            ROOT / "data/v2/place_platform_v2.sqlite3",
            ROOT / "data/v2/staging/user_web",
            "ปราจีนบุรี",
            rebuild_staging=True,
        )

    def test_y701_current_snapshot_is_ready_for_cutover(self):
        r = self.get()
        self.assertEqual(r["status"], "READY_FOR_CUTOVER")
        self.assertEqual(r["eligible_place_count"], 220)
        self.assertEqual(r["blocked_place_count"], 0)

    def test_y702_staging_covers_all_current_eligible_places(self):
        r = self.get()
        self.assertEqual(r["staging_eligible_place_count"], 220)
        self.assertEqual(r["staging_overlay_place_count"], 220)

    def test_y703_existing_release_gates_all_pass(self):
        r = self.get()
        self.assertEqual(r["comparative_status"], "PASS")
        self.assertEqual(r["production_readiness_status"], "READY")
        self.assertEqual(r["switch_plan_status"], "READY_TO_SWITCH")
        self.assertTrue(r["rollback_verified"])

    def test_y704_gate_is_read_only_for_production(self):
        before = {f: (ROOT / f).read_bytes() for f in FILES}
        r = self.get()
        self.assertFalse(r["production_json_changed"])
        self.assertFalse(r["public_user_web_switched"])
        self.assertEqual(before, {f: (ROOT / f).read_bytes() for f in FILES})


if __name__ == "__main__":
    unittest.main()
