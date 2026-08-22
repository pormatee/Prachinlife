from __future__ import annotations

import unittest
from pathlib import Path


ADMIN = Path("admin.html")
CSS = Path("admin.css")
JS = Path("js/admin/admin.js")


class TestPhase2T1AdminWebFoundation(unittest.TestCase):
    def test_t101_admin_page_exists_and_is_noindex(self):
        self.assertTrue(ADMIN.exists())
        text = ADMIN.read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', text)
        self.assertIn("Phase 2T Foundation", text)

    def test_t102_admin_is_internal_runtime_only(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("internalRuntimeAllowed", text)
        self.assertIn('"localhost"', text)
        self.assertIn('"127.0.0.1"', text)
        self.assertIn("document.querySelectorAll", text)
        self.assertIn("node.disabled = true", text)

    def test_t103_admin_reads_v2_export_without_db_write(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('data/v2/exports/prachinlife_places_v2.json', text)
        self.assertIn("fetch(EXPORT_URL", text)
        self.assertNotIn("sqlite", text.lower())
        self.assertNotIn("save_place", text)
        self.assertNotIn("apply_adoption", text)

    def test_t104_admin_can_search_and_select_existing_place(self):
        html = ADMIN.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        self.assertIn('id="adminPlaceSearch"', html)
        self.assertIn('id="adminPlaceSelect"', html)
        self.assertIn("renderPlaceOptions", js)
        self.assertIn("populateSelectedPlace", js)

    def test_t105_foundation_covers_priority_detail_fields(self):
        html = ADMIN.read_text(encoding="utf-8")
        for field in (
            "fieldDistrict", "fieldSubdistrict", "fieldArea", "fieldOpeningHours",
            "fieldPhone", "fieldWebsite", "fieldRealImage", "fieldDescription",
        ):
            self.assertIn(f'id="{field}"', html)

    def test_t106_source_provenance_is_required_in_draft(self):
        html = ADMIN.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        self.assertIn('id="adminSourceName" required', html)
        self.assertIn('id="adminSourceUrl" required', html)
        self.assertIn("source_name", js)
        self.assertIn("source_url", js)
        self.assertIn("http(s)", js)

    def test_t107_output_is_evidence_draft_only(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('mode: "evidence_draft_only"', text)
        self.assertIn('intake: "admin_web"', text)
        self.assertIn('schema_version: CONTRACT_VERSION', text)
        self.assertNotIn("public_production", text)

    def test_t108_admin_ui_is_mobile_responsive(self):
        self.assertTrue(CSS.exists())
        text = CSS.read_text(encoding="utf-8")
        self.assertIn("@media (max-width:720px)", text)
        self.assertIn("grid-template-columns:1fr", text)

    def test_t109_main_public_index_does_not_expose_admin_link(self):
        text = Path("index.html").read_text(encoding="utf-8")
        self.assertNotIn('href="admin.html"', text)

    def test_t110_admin_field_contract_remains_canonical_boundary(self):
        text = Path("place_platform_v2/admin_fields.py").read_text(encoding="utf-8")
        self.assertIn("build_admin_evidence", text)
        self.assertIn("EvidenceStatus.CANDIDATE", text)
        self.assertNotIn("save_place(", text)


if __name__ == "__main__":
    unittest.main()
