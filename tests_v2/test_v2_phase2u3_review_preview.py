from pathlib import Path
import unittest

ROOT=Path('.')
ADMIN=(ROOT/'admin.html').read_text(encoding='utf-8')
REVIEW=(ROOT/'admin-review.html').read_text(encoding='utf-8')
ADMIN_JS=(ROOT/'js/admin/admin.js').read_text(encoding='utf-8')
REVIEW_JS=(ROOT/'js/admin/review.js').read_text(encoding='utf-8')
PREVIEW=(ROOT/'js/admin/preview.js').read_text(encoding='utf-8')
SERVER=(ROOT/'scripts/admin_internal_server.py').read_text(encoding='utf-8')

class TestPhase2U3ReviewPreview(unittest.TestCase):
    def test_u301_shared_preview_renderer_exists(self):
        self.assertIn('PrachinLifeAdminPreview', PREVIEW)
        self.assertIn('renderCard', PREVIEW)
        self.assertIn('applyChanges', PREVIEW)

    def test_u302_editor_has_visual_preview_panel(self):
        self.assertIn('adminBeforeAfterPreview', ADMIN)
        self.assertIn('ตัวอย่างก่อนบันทึก', ADMIN)
        self.assertIn('ต้องตรวจ Preview ก่อนบันทึก', ADMIN)

    def test_u303_editor_renders_before_after(self):
        self.assertIn('renderEditorPreview', ADMIN_JS)
        self.assertIn('ก่อนปรับปรุง', ADMIN_JS)
        self.assertIn('หลังปรับปรุง', ADMIN_JS)

    def test_u304_save_disabled_until_draft_preview(self):
        self.assertIn('byId("adminSaveDraftBtn").disabled = true', ADMIN_JS)
        self.assertIn('renderEditorPreview(currentDraft)', ADMIN_JS)
        self.assertIn('byId("adminSaveDraftBtn").disabled = false', ADMIN_JS)

    def test_u305_reviewer_loads_current_export_for_before(self):
        self.assertIn('prachinlife_places_v2.json', REVIEW_JS)
        self.assertIn('placesById', REVIEW_JS)
        self.assertIn('basePlace(item)', REVIEW_JS)

    def test_u306_reviewer_renders_before_after(self):
        self.assertIn('previewHtml(item)', REVIEW_JS)
        self.assertIn('ก่อนปรับปรุง', REVIEW_JS)
        self.assertIn('หลังปรับปรุง', REVIEW_JS)
        self.assertIn('applyChanges', REVIEW_JS)

    def test_u307_review_actions_follow_preview(self):
        preview_pos=REVIEW_JS.find('${previewHtml(item)}')
        approve_pos=REVIEW_JS.find('data-review-decision="approved"')
        self.assertGreaterEqual(preview_pos,0)
        self.assertGreater(approve_pos, preview_pos)

    def test_u308_review_page_loads_preview_contract(self):
        self.assertRegex(REVIEW, r'js/admin/preview\.js\?v=phase2u3(?:1|2|31)-20260822')
        self.assertIn('js/core/place-image.js', REVIEW)

    def test_u309_editor_page_loads_preview_contract(self):
        self.assertRegex(ADMIN, r'js/admin/preview\.js\?v=phase2u3(?:1|31)-20260822')
        self.assertRegex(ADMIN, r'js/admin/admin\.js\?v=phase2u(?:3|33|331)-20260822')

    def test_u310_no_canonical_or_publication_enable(self):
        combined='\n'.join((ADMIN_JS,REVIEW_JS,PREVIEW,SERVER))
        self.assertIn('Canonical writes: DISABLED', SERVER)
        self.assertIn('Publication: DISABLED', SERVER)
        self.assertNotIn('canonical_write=True', combined)
        self.assertNotIn('publication=True', combined)

    def test_u311_server_phase_updated(self):
        self.assertIn('PrachinLifeAdmin/2U.3', SERVER)
        self.assertRegex(SERVER, r'"phase":"2U\.3(?:\.[23](?:\.[12])?)?"')

    def test_u312_preview_is_responsive(self):
        css=(ROOT/'admin.css').read_text(encoding='utf-8')
        self.assertIn('.admin-before-after-preview', css)
        self.assertIn('@media(max-width:760px)', css)

if __name__=='__main__': unittest.main()
