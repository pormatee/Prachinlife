import unittest
from pathlib import Path

ROOT=Path('.')
ADMIN=(ROOT/'js/admin/admin.js').read_text(encoding='utf-8')
REVIEW=(ROOT/'js/admin/review.js').read_text(encoding='utf-8')
PREVIEW=(ROOT/'js/admin/preview.js').read_text(encoding='utf-8')
HTML=(ROOT/'admin-review.html').read_text(encoding='utf-8')

class TestPhase2U335ReviewSemantics(unittest.TestCase):
    def test_u335_01_payload_keeps_review_context(self):
        self.assertIn('review_context:', ADMIN)
        self.assertIn('seed_snapshot:', ADMIN)
        self.assertIn('operator_changes:', ADMIN)

    def test_u335_02_operator_changes_compare_legacy_seed(self):
        self.assertIn('buildOperatorChanges', ADMIN)
        self.assertIn('snapshotPlace(legacySeedPlace)', ADMIN)

    def test_u335_03_review_separates_seed_from_operator_changes(self):
        self.assertIn('ข้อมูลตั้งต้นที่จะสร้างใน V2', REVIEW)
        self.assertIn('สิ่งที่ Admin เปลี่ยน / เติมในรอบนี้', REVIEW)

    def test_u335_04_description_is_reviewable(self):
        self.assertIn('description:"รายละเอียด"', REVIEW)
        self.assertIn('["description", "fieldDescription"', ADMIN)

    def test_u335_05_real_image_is_reviewable(self):
        self.assertIn('real_image:"รูปจริง"', REVIEW)
        self.assertIn('["real_image", "fieldRealImage"', ADMIN)

    def test_u335_06_legacy_seed_renders_before_card(self):
        self.assertIn('hasLegacySeed(item)', REVIEW)
        self.assertIn('"ข้อมูลตั้งต้น"', REVIEW)

    def test_u335_07_direct_media_url_is_rendered_first(self):
        self.assertIn('const direct = text(place?.real_image || place?.image_url || place?.image)', PREVIEW)
        self.assertIn('src="${esc(direct)}"', PREVIEW)

    def test_u335_08_cache_bust(self):
        self.assertIn('phase2u331-20260822-u335', HTML)

if __name__ == '__main__':
    unittest.main()
