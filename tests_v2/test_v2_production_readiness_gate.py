from __future__ import annotations
import unittest
from pathlib import Path
from place_platform_v2.production_readiness_gate import audit_production_readiness
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    def get(self):
        return audit_production_readiness(ROOT,ROOT/'data/v2/place_platform_v2.sqlite3',ROOT/'data/v2/staging/user_web')
    def test_current_snapshot_is_ready_but_not_switched(self):
        r=self.get();self.assertEqual(r['status'],'READY');self.assertFalse(r['production_switch_performed']);self.assertFalse(r['public_user_web_switched'])
    def test_fresh_comparative_supersedes_phase2h(self):
        r=self.get();self.assertEqual(r['comparative_status'],'PASS');self.assertTrue(r['phase2h_superseded'])
    def test_rollback_verified(self):
        self.assertTrue(self.get()['rollback_verified'])
    def test_no_blockers(self):
        self.assertEqual(self.get()['blockers'],[])
if __name__=='__main__': unittest.main()
