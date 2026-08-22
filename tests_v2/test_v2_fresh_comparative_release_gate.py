from __future__ import annotations
import unittest
from pathlib import Path
from place_platform_v2.comparative_release_gate import audit_fresh_comparative_release
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    def get(self):
        return audit_fresh_comparative_release(ROOT,ROOT/'data/v2/place_platform_v2.sqlite3',ROOT/'data/v2/staging/user_web')
    def test_passes_current_overlay_snapshot(self):
        r=self.get();self.assertEqual(r['status'],'PASS');self.assertEqual(r['eligible_place_count'],20);self.assertEqual(r['overlay_place_count'],20)
    def test_preserves_all_v1_counts(self):
        r=self.get();
        for x in r['files'].values(): self.assertEqual(x['v1_count'],x['staged_count'])
    def test_fallback_rows_are_unchanged(self):
        self.assertEqual(self.get()['fallback_mutations'],[])
    def test_overlay_core_identity_matches_canonical(self):
        self.assertEqual(self.get()['overlay_core_mismatches'],[])
    def test_rollback_is_verified(self):
        self.assertTrue(self.get()['rollback_verified'])
    def test_never_switches_production(self):
        r=self.get();self.assertEqual(r['production_switch'],'DISABLED');self.assertFalse(r['public_user_web_switched'])
if __name__=='__main__': unittest.main()
