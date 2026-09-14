from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.css"
JS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.js"
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeMobileAiComposerV122(unittest.TestCase):
    def test_01_production_root_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_mobile_breakpoint_covers_large_phones(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 900px)", text)

    def test_03_mobile_chat_is_true_fixed_overlay(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn("position: fixed !important", text)
        self.assertIn("height: var(--ai-vv-height, 100dvh) !important", text)
        self.assertIn("z-index: 3000 !important", text)
        self.assertIn(".legacy-preview-hero .robot-assist-panel[hidden]", text)

    def test_04_messages_scroll_inside_panel_not_page(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn("flex: 1 1 auto !important", text)
        self.assertIn("overflow-y: auto !important", text)
        self.assertIn("overscroll-behavior: contain", text)

    def test_05_composer_is_always_last_visible_flex_item(self):
        text = CSS.read_text(encoding="utf-8")
        self.assertIn(".robot-assist-composer", text)
        self.assertIn("flex: 0 0 auto", text)
        self.assertIn("env(safe-area-inset-bottom", text)

    def test_06_visual_viewport_handles_android_keyboard(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("window.visualViewport", text)
        self.assertIn('visualViewport.addEventListener("resize"', text)
        self.assertIn('visualViewport.addEventListener("scroll"', text)
        # R6 superseded CSS custom-property viewport transport with direct
        # VisualViewport measurements while preserving the keyboard behavior.
        self.assertIn("viewport.height", text)
        self.assertIn("viewport.offsetTop", text)

    def test_07_open_locks_page_and_close_unlocks(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("function lockAssistantPage", text)
        self.assertIn("function unlockAssistantPage", text)
        self.assertIn('classList.add("ai-chat-open")', text)
        self.assertIn('classList.remove("ai-chat-open")', text)

    def test_08_focus_uses_prevent_scroll(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("focus({ preventScroll: true })", text)

    def test_09_ai_architecture_remains_provider_neutral(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("ctx.endpoints.decision", text)
        for forbidden in ("api.openai.com", "api.deepseek.com", "anthropic.com"):
            self.assertNotIn(forbidden, text)

    def test_10_no_auto_geolocation_added(self):
        text = JS.read_text(encoding="utf-8")
        self.assertNotIn("navigator.geolocation", text)
        self.assertNotIn("getCurrentPosition", text)

if __name__ == "__main__":
    unittest.main()
