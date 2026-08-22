from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "admin-view.html"
VIEW_JS = ROOT / "js/admin/admin-view.js"
VIEW_CSS = ROOT / "admin-view.css"
ADMIN = ROOT / "admin.html"
ADMIN_JS = ROOT / "js/admin/admin.js"
APP = ROOT / "app.js"
VEG = ROOT / "js/modules/vegetarian.js"
GO = ROOT / "js/modules/go.js"
SERVICE = ROOT / "js/modules/service.js"

class TestPhase2T3UserLikeAdminView(unittest.TestCase):
    def test_t301_user_like_admin_page_exists(self):
        self.assertTrue(VIEW.exists())
        text = VIEW.read_text(encoding="utf-8")
        self.assertIn('id="eatList"', text)
        self.assertIn('id="vegetarianList"', text)
        self.assertIn('id="goList"', text)
        self.assertIn('id="serviceList"', text)

    def test_t302_admin_overlay_loaded_on_user_view(self):
        text = VIEW.read_text(encoding="utf-8")
        self.assertRegex(text, r'admin-view\.css\?v=phase2t[34]-20260822')
        self.assertRegex(text, r'js/admin/admin-view\.js\?v=phase2t[34]-20260822')
        self.assertIn('ADMIN MODE', text)

    def test_t303_place_cards_expose_stable_ids_without_visual_change(self):
        for path in (APP, VEG, GO, SERVICE):
            text = path.read_text(encoding="utf-8")
            self.assertIn('data-place-id=', text, path.name)

    def test_t304_edit_button_links_to_existing_form(self):
        text = VIEW_JS.read_text(encoding="utf-8")
        self.assertIn('admin.html?place_id=', text)
        self.assertIn('แก้ไข / ปรับปรุงข้อมูล', text)

    def test_t305_admin_form_preloads_query_place(self):
        text = ADMIN_JS.read_text(encoding="utf-8")
        self.assertIn('params.get("place_id")', text)
        self.assertIn('populateSelectedPlace(requestedPlace, true)', text)
        self.assertIn('โหลดข้อมูลปัจจุบัน', text)

    def test_t306_new_place_link_reuses_same_form(self):
        view = VIEW.read_text(encoding="utf-8")
        admin_js = ADMIN_JS.read_text(encoding="utf-8")
        self.assertIn('admin.html?mode=new#adminEditPanel', view)
        self.assertIn('requestedMode === "new"', admin_js)
        self.assertIn('startNewPlace()', admin_js)

    def test_t307_v2_cards_edit_directly_and_legacy_cards_use_safe_candidate_handoff(self):
        text = VIEW_JS.read_text(encoding="utf-8")
        self.assertIn('editableIds.has(placeId)', text)
        self.assertIn('legacyPlaces.has(placeId)', text)
        self.assertIn('mode=legacy', text)
        self.assertIn('เพิ่ม / ปรับปรุงเข้าสู่ V2', text)

    def test_t308_internal_only_boundary_preserved(self):
        for path in (VIEW_JS, ADMIN_JS):
            text = path.read_text(encoding="utf-8")
            self.assertIn('127.0.0.1', text)
            self.assertIn('internalRuntimeAllowed', text)

    def test_t309_evidence_draft_only_preserved(self):
        text = ADMIN_JS.read_text(encoding="utf-8")
        self.assertIn('mode: "evidence_draft_only"', text)
        self.assertNotIn('UPDATE places SET', text)
        self.assertNotIn('INSERT INTO places', text)

    def test_t310_admin_view_is_noindex(self):
        text = VIEW.read_text(encoding="utf-8")
        self.assertIn('noindex,nofollow,noarchive', text)

    def test_t311_mutation_observer_handles_runtime_rerender(self):
        text = VIEW_JS.read_text(encoding="utf-8")
        self.assertIn('MutationObserver', text)
        self.assertIn('decorateAllCards', text)

    def test_t312_public_index_does_not_load_admin_overlay(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('admin-view.js', text)
        self.assertNotIn('admin-view.css', text)

if __name__ == '__main__': unittest.main()
