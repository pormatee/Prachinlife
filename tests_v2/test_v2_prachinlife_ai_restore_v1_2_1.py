from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "prachinburi/index.html"
CSS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.css"
JS = ROOT / "regional_products/prachinburi/web/legacy-experience-v1.js"
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeAiRestoreV121(unittest.TestCase):
    def test_01_production_root_remains_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_approved_ai_styles_are_reused(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("../css/locallife-decision-card-v1.css", text)
        self.assertIn('class="ai-assistant-feature"', text)
        self.assertIn('class="robot-assist-panel"', text)

    def test_03_ai_ui_is_visible_as_prachinlife_feature(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("ผู้ช่วย AI PrachinLife", text)
        self.assertIn('id="aiAssistantOpen"', text)
        self.assertIn('id="robotAssistInput"', text)
        self.assertIn('id="robotAssistSend"', text)

    def test_04_decision_endpoint_comes_from_regional_context(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("ctx.endpoints.decision", text)
        self.assertIn("decisionEndpoint = ctx.endpoints.decision", text)
        self.assertNotIn('decisionEndpoint = "/v1/decision"', text)

    def test_05_ai_calls_only_locallife_decision_api(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn('method: "POST"', text)
        self.assertIn('"Content-Type": "application/json"', text)
        for forbidden in ("api.openai.com", "api.deepseek.com", "anthropic.com"):
            self.assertNotIn(forbidden, text)

    def test_06_conversation_state_is_preserved(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("conversationState", text)
        self.assertIn("{ conversation_state: conversationState }", text)
        self.assertIn("payload.result.conversation_state", text)

    def test_07_fail_closed_message_is_present(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("ระบบจะไม่เดาคำตอบให้", text)
        self.assertIn("regional context mismatch", text)

    def test_08_no_direct_domain_data_files(self):
        text = PAGE.read_text(encoding="utf-8") + JS.read_text(encoding="utf-8")
        for forbidden in (
            "prachinlife_index.json",
            "vegetarian_index.json",
            "go_index.json",
            "service_index.json",
            "place_platform_v2.sqlite3",
        ):
            self.assertNotIn(forbidden, text)

    def test_09_no_html_injection_surface(self):
        text = JS.read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", text)
        self.assertNotIn("insertAdjacentHTML", text)
        self.assertIn("textContent", text)

    def test_10_near_me_still_does_not_auto_request_location(self):
        text = JS.read_text(encoding="utf-8")
        self.assertNotIn("navigator.geolocation", text)
        self.assertNotIn("getCurrentPosition", text)

    def test_11_ai_controls_support_open_close_reset(self):
        text = JS.read_text(encoding="utf-8")
        self.assertIn("function openAssistant", text)
        self.assertIn("function closeAssistant", text)
        self.assertIn("function resetAssistant", text)

    def test_12_regional_ai_adapter_does_not_modify_generic_shell(self):
        self.assertTrue(CSS.is_file())
        self.assertTrue(JS.is_file())
        self.assertIn("regional_products/prachinburi/web", str(JS).replace("\\", "/"))

if __name__ == "__main__":
    unittest.main()
