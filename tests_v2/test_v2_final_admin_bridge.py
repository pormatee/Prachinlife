from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class FinalAdminBridgeTest(unittest.TestCase):
    def test_01_review_has_process3_builder(self):
        t=(ROOT/'js/admin/review.js').read_text(encoding='utf-8'); self.assertIn('function process3Links(item)',t)
    def test_02_only_approved_noncommunity(self):
        t=(ROOT/'js/admin/review.js').read_text(encoding='utf-8'); self.assertIn('item.status!=="approved"',t); self.assertIn('communityReport(item)',t)
    def test_03_only_phase16_fields_linked(self):
        t=(ROOT/'js/admin/review.js').read_text(encoding='utf-8'); self.assertIn('c.field_name==="phone"||c.field_name==="website"',t)
    def test_04_bridge_points_to_verified_update(self):
        t=(ROOT/'js/admin/review.js').read_text(encoding='utf-8'); self.assertIn('admin-verified-update.html?',t); self.assertIn('data-process3-link',t)
    def test_05_verified_page_prefills_query(self):
        t=(ROOT/'js/admin/verified-update.js').read_text(encoding='utf-8'); self.assertIn('function prefillFromQuery()',t); self.assertIn('from_approved_draft',t)
    def test_06_publish_confirmation_preserved(self):
        t=(ROOT/'js/admin/verified-update.js').read_text(encoding='utf-8'); self.assertIn('PUBLISH_VERIFIED_UPDATE',t); self.assertIn('/api/admin/verified-update/commit',t)
    def test_07_community_hold_server_preserved(self):
        t=(ROOT/'place_platform_v2/admin_drafts.py').read_text(encoding='utf-8'); self.assertIn('community report is HOLD-only',t)
    def test_08_phase16_guard_preserved(self):
        t=(ROOT/'place_platform_v2/phase16_verified_update.py').read_text(encoding='utf-8'); self.assertIn('automatic_unverified_publication',t)
if __name__=='__main__': unittest.main()
