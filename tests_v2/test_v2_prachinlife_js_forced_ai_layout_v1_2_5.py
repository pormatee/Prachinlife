from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "prachinburi/index.html"
JS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.js"
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeJsForcedAiLayoutV125(unittest.TestCase):
    def test_01_production_root_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_cache_bust_advances_to_r6(self):
        text = PAGE.read_text(encoding="utf-8")
        # R6 body-portal is the current successor of the R5 forced-layout fix.
        self.assertIn("legacy-experience-v1.js?v=12r6", text)
        self.assertIn("Web Preview R6", text)

    def test_03_js_forces_panel_layout_directly(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("function forceMobileAssistantLayout", text)
        self.assertIn('setImportant(aiPanel, "position", "fixed")', text)
        self.assertIn('setImportant(aiPanel, "display", "flex")', text)
        self.assertIn('setImportant(aiPanel, "height"', text)

    def test_04_js_forces_message_scroll_and_composer_position(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('setImportant(aiMessages, "overflow-y", "auto")', text)
        self.assertIn('setImportant(composer, "flex", "0 0 auto")', text)
        self.assertIn('setImportant(composer, "position", "relative")', text)

    def test_05_visual_viewport_still_used(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("window.visualViewport", text)
        self.assertIn("viewport.height", text)
        self.assertIn("viewport.offsetTop", text)

    def test_06_touch_devices_are_supported(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("navigator.maxTouchPoints", text)

    def test_07_ai_endpoint_remains_regional(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("ctx.endpoints.decision", text)
        self.assertIn('method: "POST"', text)
        for forbidden in ("api.openai.com", "api.deepseek.com", "anthropic.com"):
            self.assertNotIn(forbidden, text)

    def test_08_no_auto_geolocation(self):
        text = JS.read_text(encoding="utf-8")
        self.assertNotIn("navigator.geolocation", text)
        self.assertNotIn("getCurrentPosition", text)

if __name__ == "__main__":
    unittest.main()
