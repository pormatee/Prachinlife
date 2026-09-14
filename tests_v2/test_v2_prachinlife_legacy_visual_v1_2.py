from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "prachinburi/index.html"
CSS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.css"
JS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.js"

EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeLegacyVisualReuseV12(unittest.TestCase):
    def test_01_production_root_is_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_preview_reuses_approved_visual_system(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('../style.css?v=legacy-visual-reuse-v1', text)
        self.assertIn('class="site-header"', text)
        self.assertIn('class="hero', text)
        self.assertIn('class="control-main-grid', text)

    def test_03_preview_reuses_real_brand_and_category_assets(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("../assets/brand/prachinlife-icon-v1.png", text)
        self.assertIn("../assets/images/icons/soft3d/shopping.png", text)
        self.assertIn("../assets/images/icons/soft3d/eat.png", text)
        self.assertIn("../assets/images/icons/jay-icon.jpeg", text)

    def test_04_visual_categories_match_prachinlife_experience(self):
        text = PAGE.read_text(encoding="utf-8")
        for label in ("แนะนำ", "ช้อป", "กิน", "เจ / มังสวิรัติ", "เที่ยว", "บริการ", "ใกล้ฉัน"):
            self.assertIn(label, text)

    def test_05_page_remains_additive_preview_route(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('data-region="prachinburi"', text)
        self.assertIn('data-view="home"', text)
        self.assertIn('data-context-endpoint="/v1/regions/prachinburi/context"', text)
        self.assertIn("Web Preview", text)
        self.assertIn('name="robots" content="noindex,nofollow"', text)

    def test_06_no_direct_domain_data_file_is_embedded(self):
        text = PAGE.read_text(encoding="utf-8") + JS.read_text(encoding="utf-8")
        for forbidden in (
            "prachinlife_index.json",
            "vegetarian_index.json",
            "go_index.json",
            "service_index.json",
            "place_platform_v2.sqlite3",
        ):
            self.assertNotIn(forbidden, text)

    def test_07_runtime_uses_get_for_context_and_post_only_for_decision_api(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('locallife.regional-web-context/v1', text)
        self.assertIn('method: "GET"', text)
        self.assertIn('method: "POST"', text)
        self.assertIn("ctx.endpoints.decision", text)
        self.assertIn("decisionEndpoint = ctx.endpoints.decision", text)
        self.assertNotIn('method: "PUT"', text)
        self.assertNotIn('method: "DELETE"', text)
        for forbidden in ("api.openai.com", "api.deepseek.com", "anthropic.com"):
            self.assertNotIn(forbidden, text)

    def test_08_api_override_remains_restricted(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('parsed.hostname === "127.0.0.1"', text)
        self.assertIn('parsed.hostname === "localhost"', text)
        self.assertIn("sameOrigin", text)
        self.assertIn("apiBase is not allowed", text)

    def test_09_preview_does_not_request_geolocation(self):
        text = JS.read_text(encoding="utf-8")
        self.assertNotIn("navigator.geolocation", text)
        self.assertNotIn("getCurrentPosition", text)

    def test_10_regional_adapter_is_separate_from_generic_shell(self):
        self.assertTrue(CSS.is_file())
        self.assertTrue(JS.is_file())
        self.assertIn("regional_products/prachinburi/web", str(CSS).replace("\\", "/"))
        self.assertIn("regional_products/prachinburi/web", str(JS).replace("\\", "/"))

if __name__ == "__main__":
    unittest.main()
