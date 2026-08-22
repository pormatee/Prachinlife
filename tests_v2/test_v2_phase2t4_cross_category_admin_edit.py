from __future__ import annotations

import json
import unittest
from pathlib import Path


ADMIN_VIEW_JS = Path("js/admin/admin-view.js")
ADMIN_JS = Path("js/admin/admin.js")
ADMIN_VIEW_HTML = Path("admin-view.html")
ADMIN_HTML = Path("admin.html")
EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")


class TestPhase2T4CrossCategoryAdminEdit(unittest.TestCase):

    def test_t401_admin_view_knows_all_legacy_category_sources(self):
        text = ADMIN_VIEW_JS.read_text(encoding="utf-8")
        for marker in (
            'eat: "prachinlife_index.json"',
            'vegetarian: "vegetarian_index.json"',
            'go: "go_index.json"',
            'service: "service_index.json"',
        ):
            self.assertIn(marker, text)

    def test_t402_legacy_cards_have_safe_handoff_path(self):
        text = ADMIN_VIEW_JS.read_text(encoding="utf-8")
        self.assertIn("LEGACY_HANDOFF_KEY", text)
        self.assertIn("sessionStorage.setItem", text)
        self.assertIn("mode=legacy", text)
        self.assertIn("เพิ่ม / ปรับปรุงเข้าสู่ V2", text)

    def test_t403_admin_form_reads_legacy_handoff(self):
        text = ADMIN_JS.read_text(encoding="utf-8")
        self.assertIn("readLegacyHandoff", text)
        self.assertIn("populateLegacyPlace", text)
        self.assertIn('requestedMode === "legacy"', text)

    def test_t404_legacy_handoff_is_create_candidate_not_canonical_update(self):
        text = ADMIN_JS.read_text(encoding="utf-8")
        self.assertIn('operation: createMode ? "create_place_candidate" : "update_place_candidate"', text)
        self.assertIn("legacy_context", text)
        self.assertIn("evidence_draft_only", text)
        self.assertNotIn("UPDATE places SET", text)
        self.assertNotIn("INSERT INTO places", text)

    def test_t405_legacy_preload_includes_user_visible_detail_fields(self):
        text = ADMIN_JS.read_text(encoding="utf-8")
        for field in (
            "fieldCanonicalName", "fieldProvince", "fieldDistrict", "fieldSubdistrict",
            "fieldArea", "fieldAddress", "fieldLatitude", "fieldLongitude",
            "fieldOpeningHours", "fieldPhone", "fieldWebsite", "fieldRealImage",
            "fieldCategories", "fieldDescription", "adminSourceName", "adminSourceUrl",
        ):
            self.assertIn(field, text)

    def test_t406_v2_export_has_all_four_place_groups(self):
        places = json.loads(EXPORT.read_text(encoding="utf-8"))["places"]
        groups = set()
        for place in places:
            cats = set(place.get("categories") or [])
            if cats & {"vegetarian", "vegan", "jay"}:
                groups.add("vegetarian")
            if cats & {"restaurant", "cafe", "fast_food", "food_court", "ice_cream"}:
                groups.add("eat")
            if cats & {"attraction", "temple", "park", "nature", "tourism"}:
                groups.add("go")
            if cats & {"fuel", "pharmacy", "clinic", "car_repair", "laundry", "hospital", "bank", "atm"}:
                groups.add("service")
        self.assertEqual(groups, {"eat", "vegetarian", "go", "service"})

    def test_t407_admin_cache_bust_is_phase2t4(self):
        self.assertIn("phase2t4-20260822", ADMIN_VIEW_HTML.read_text(encoding="utf-8"))
        self.assertRegex(ADMIN_HTML.read_text(encoding="utf-8"), r"phase2(?:t4|u1|u2|u3|u33|u331)-20260822")

    def test_t408_public_index_has_no_admin_overlay(self):
        public = Path("index.html").read_text(encoding="utf-8")
        self.assertNotIn("js/admin/admin-view.js", public)
        self.assertNotIn("admin-view-toolbar", public)


if __name__ == "__main__":
    unittest.main()
