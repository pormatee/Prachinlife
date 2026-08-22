from __future__ import annotations
import unittest
from pathlib import Path

HTML = Path("admin.html")
CSS = Path("admin.css")
JS = Path("js/admin/admin.js")


class TestPhase2T2VisualAdminPlaceManager(unittest.TestCase):
    def test_t201_visual_card_manager_exists(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('id="adminPlaceCards"', html)
        self.assertIn('id="adminAddPlaceBtn"', html)
        self.assertIn("Visual Place Manager", html)

    def test_t202_admin_cards_share_place_image_contract(self):
        html = HTML.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        self.assertIn("js/core/place-image.js", html)
        self.assertIn("placeImage.renderPlaceImage", js)
        self.assertIn("fallbackGroup", js)

    def test_t203_card_edit_opens_existing_form(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("data-admin-edit-id", js)
        self.assertIn("populateSelectedPlace(place, true)", js)
        self.assertIn('byId("adminEditPanel").scrollIntoView', js)

    def test_t204_completeness_exposes_priority_missing_fields(self):
        js = JS.read_text(encoding="utf-8")
        for field in ("district", "subdistrict", "area", "opening_hours", "phone", "website", "real_image", "description"):
            self.assertIn(f'"{field}"', js)
        self.assertIn("function completeness", js)
        self.assertIn("admin-missing-chip", js)

    def test_t205_add_new_place_reuses_same_form(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("function startNewPlace", js)
        self.assertIn('operation: createMode ? "create_place_candidate" : "update_place_candidate"', js)
        self.assertIn("place_id: selectedPlace?.id || null", js)

    def test_t206_new_place_requires_core_identity(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("สถานที่ใหม่ต้องมีชื่อสถานที่", js)
        self.assertIn("สถานที่ใหม่ต้องระบุจังหวัด", js)
        self.assertIn("สถานที่ใหม่ต้องมีอย่างน้อย 1 หมวด", js)
        self.assertIn("readLocation(", js)
        self.assertIn("createMode", js)

    def test_t207_still_evidence_draft_only(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn('mode: "evidence_draft_only"', js)
        self.assertNotIn("sqlite", js.lower())
        self.assertNotIn("save_place", js)
        self.assertNotIn("apply_adoption", js)

    def test_t208_source_provenance_remains_required(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("กรุณาระบุชื่อแหล่งข้อมูล", js)
        self.assertIn("กรุณาระบุ URL แหล่งข้อมูลแบบ http(s)", js)
        self.assertIn("source_name: sourceName", js)
        self.assertIn("source_url: sourceUrl", js)

    def test_t209_mobile_visual_cards_are_single_column(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".admin-place-grid", css)
        self.assertIn("@media (max-width:720px)", css)
        self.assertIn("grid-template-columns:1fr", css)

    def test_t210_public_index_still_has_no_admin_link(self):
        public = Path("index.html").read_text(encoding="utf-8")
        self.assertNotIn('href="admin.html"', public)

    def test_t211_existing_phase2t1_search_select_ids_preserved(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('id="adminPlaceSearch"', html)
        self.assertIn('id="adminPlaceSelect"', html)
        self.assertIn('id="adminBuildDraftBtn"', html)

    def test_t212_no_public_production_switch(self):
        combined = HTML.read_text(encoding="utf-8") + JS.read_text(encoding="utf-8")
        self.assertNotIn("public_production", combined)
        self.assertNotIn("Public Production", combined)


if __name__ == "__main__":
    unittest.main()
