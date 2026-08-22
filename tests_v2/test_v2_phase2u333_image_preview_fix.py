from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
PLACE=(ROOT/'js/core/place-image.js').read_text(encoding='utf-8')
ADMIN=(ROOT/'js/admin/admin.js').read_text(encoding='utf-8')
REVIEW=(ROOT/'js/admin/review.js').read_text(encoding='utf-8')
HTML=(ROOT/'admin.html').read_text(encoding='utf-8')
REVIEW_HTML=(ROOT/'admin-review.html').read_text(encoding='utf-8')
class TestPhase2U333ImagePreviewFix(unittest.TestCase):
    def test_real_image_is_first_class_image_candidate(self):
        self.assertIn('place?.real_image', PLACE)
        self.assertIn('metadata?.real_image', PLACE)
    def test_file_selection_auto_uploads(self):
        self.assertIn('imageUploadInFlight = uploadSelectedImage()', ADMIN)
    def test_draft_waits_for_upload(self):
        self.assertIn('if (imageUploadInFlight)', ADMIN)
        self.assertIn('รูปที่เลือกยังอัปโหลดไม่สำเร็จ', ADMIN)
    def test_review_after_preview_applies_real_image(self):
        self.assertIn('case "real_image": next.real_image = value; next.image_url = value;', (ROOT/'js/admin/preview.js').read_text(encoding='utf-8'))
        self.assertIn('field_name==="real_image"', REVIEW)
    def test_cache_bust(self):
        self.assertIn('u333', HTML)
        self.assertIn('u333', REVIEW_HTML)
    def test_no_canonical_write(self):
        server=(ROOT/'scripts/admin_internal_server.py').read_text(encoding='utf-8')
        self.assertIn('Canonical writes: DISABLED', server)
if __name__=='__main__': unittest.main()
