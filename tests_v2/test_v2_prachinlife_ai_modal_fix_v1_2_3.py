from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "prachinburi/index.html"
CSS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.css"
JS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.js"
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeAiModalFixV123(unittest.TestCase):
    def test_01_production_root_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_asset_urls_are_cache_busted_for_current_r6(self):
        text = PAGE.read_text(encoding="utf-8")
        # R3 established the cache-busting requirement; later fixes advance
        # the asset versions without weakening that requirement.
        self.assertIn("legacy-experience-v1.css?v=12r5", text)
        self.assertIn("legacy-experience-v1.js?v=12r6", text)
        self.assertIn("locallife-decision-card-v1.css?v=regional-ai-modal-v12r3", text)

    def test_03_explicit_modal_class_is_full_viewport(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn(".robot-assist-panel.ai-chat-modal", text)
        self.assertIn("position: fixed !important", text)
        self.assertIn("height: var(--ai-vv-height, 100dvh) !important", text)
        self.assertIn("z-index: 4000 !important", text)

    def test_04_composer_cannot_drop_out_of_modal(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn(".robot-assist-panel.ai-chat-modal .robot-assist-composer", text)
        self.assertIn("flex: 0 0 auto !important", text)
        self.assertIn("padding-bottom: max(9px, env(safe-area-inset-bottom, 0px)) !important", text)

    def test_05_message_area_is_only_scroll_surface(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn(".robot-assist-panel.ai-chat-modal .robot-assist-messages", text)
        self.assertIn("overflow-y: auto !important", text)
        self.assertIn("overscroll-behavior: contain", text)

    def test_06_touch_device_forces_modal_mode(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("navigator.maxTouchPoints", text)
        self.assertIn('aiPanel.classList.add("ai-chat-modal")', text)
        self.assertIn('aiPanel.classList.remove("ai-chat-modal")', text)

    def test_07_visual_viewport_keyboard_support_remains_in_r6(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("window.visualViewport", text)
        self.assertIn("viewport.height", text)
        self.assertIn("viewport.offsetTop", text)
        self.assertIn('visualViewport.addEventListener("resize"', text)
        self.assertIn('visualViewport.addEventListener("scroll"', text)

    def test_08_ai_still_uses_regional_decision_endpoint(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("ctx.endpoints.decision", text)
        self.assertIn('method: "POST"', text)
        for forbidden in ("api.openai.com", "api.deepseek.com", "anthropic.com"):
            self.assertNotIn(forbidden, text)

    def test_09_no_auto_geolocation(self):
        text = JS.read_text(encoding="utf-8")
        self.assertNotIn("navigator.geolocation", text)
        self.assertNotIn("getCurrentPosition", text)

if __name__ == "__main__":
    unittest.main()
