from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "prachinburi/index.html"
JS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.js"
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeAiBodyPortalV126(unittest.TestCase):
    def test_01_production_root_untouched(self):
        actual = subprocess.check_output(
            ["git","hash-object","index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_cache_bust_is_r6(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("legacy-experience-v1.js?v=12r6", text)
        self.assertIn("Web Preview R6", text)

    def test_03_panel_is_portaled_to_body_on_open(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("function mountAssistantPortal", text)
        self.assertIn("document.body.appendChild(aiPanel)", text)
        self.assertIn("mountAssistantPortal();", text)

    def test_04_panel_home_is_restored_on_close(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("prachinlife-ai-panel-home", text)
        self.assertIn("function restoreAssistantHome", text)
        self.assertIn("restoreAssistantHome();", text)

    def test_05_forced_fixed_layout_is_retained(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("function forceMobileAssistantLayout", text)
        self.assertIn('setImportant(aiPanel, "position", "fixed")', text)
        self.assertIn('setImportant(aiPanel, "display", "flex")', text)

    def test_06_messages_and_composer_remain_inside_panel(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('aiPanel.querySelector(".robot-assist-composer")', text)
        self.assertIn('setImportant(aiMessages, "overflow-y", "auto")', text)

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
