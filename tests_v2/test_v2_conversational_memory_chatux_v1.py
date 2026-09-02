from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
CSS = (ROOT / "css/locallife-decision-card-v1.css").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class TestConversationalMemoryChatUxV1(unittest.TestCase):
    def test_01_browser_memory_contract_exists(self):
        self.assertIn('CHAT_MEMORY_STORAGE_KEY = "prachinlife.ai_assistant.conversation.v1"', JS)
        self.assertIn("function saveConversationMemory()", JS)
        self.assertIn("function loadConversationMemory()", JS)
        self.assertIn("function clearConversationMemory()", JS)

    def test_02_memory_is_bounded_and_clears_only_explicitly(self):
        self.assertIn("CHAT_MEMORY_MAX_MESSAGES = 80", JS)
        self.assertIn("CHAT_MEMORY_MAX_USER_TURNS = 8", JS)
        self.assertNotIn("CHAT_MEMORY_TTL_MS", JS)

    def test_03_exact_device_coordinates_are_not_persisted(self):
        start = JS.index("function persistentConversationContext()")
        end = JS.index("function normalizedStoredMessages", start)
        block = JS[start:end]
        self.assertIn("location_text", block)
        self.assertNotIn("current_location =", block)
        self.assertIn("Device coordinates are never restored from browser storage.", JS)

    def test_04_pending_clarification_survives_refresh(self):
        self.assertIn("pending_base_query:", JS)
        self.assertIn("pending_context_field:", JS)
        self.assertIn("parsed.pending_base_query", JS)
        self.assertIn("parsed.pending_context_field", JS)

    def test_05_multiturn_user_context_is_forwarded(self):
        self.assertIn("function conversationDecisionText(query, pendingWasStructured)", JS)
        self.assertIn("คำขอหลักของบทสนทนา:", JS)
        self.assertIn("บริบทจากข้อความผู้ใช้ก่อนหน้า:", JS)
        self.assertIn("ข้อความล่าสุด:", JS)
        self.assertIn("rememberUserTurn(query);", JS)

    def test_06_close_does_not_clear_memory(self):
        start = JS.index("function closeRobotAssist()")
        end = JS.index("function createRobotPanel()", start)
        block = JS[start:end]
        self.assertNotIn("clearConversationMemory()", block)
        self.assertNotIn("resetConversationState()", block)

    def test_07_explicit_new_conversation_clears_memory(self):
        self.assertIn("function startNewConversation()", JS)
        self.assertIn("resetConversationState();", JS)
        self.assertIn('reset.textContent = "เริ่มใหม่"', JS)
        self.assertIn('reset.addEventListener("click", startNewConversation)', JS)

    def test_08_chat_history_restores_on_init(self):
        self.assertIn("loadConversationMemory();", JS)
        self.assertIn("renderConversationMessages();", JS)
        self.assertIn("robotAssistStoredMessages.forEach", JS)

    def test_09_composer_is_multiline_but_enter_still_sends(self):
        self.assertIn('document.createElement("textarea")', JS)
        self.assertIn('event.key === "Enter" && !event.shiftKey', JS)

    def test_10_mobile_chat_is_large_readable_panel(self):
        self.assertIn("position: fixed !important;", CSS)
        self.assertIn("top: max(10px, env(safe-area-inset-top, 0px));", CSS)
        self.assertIn("bottom: max(8px, env(safe-area-inset-bottom, 0px));", CSS)
        self.assertIn("min-height: 220px;", CSS)

    def test_11_cache_busts_js_and_css(self):
        self.assertIn("css/locallife-decision-card-v1.css?v=conversational-memory-chatux-v1", INDEX)
        self.assertIn("conversational-memory-chatux-v1", INDEX)

    def test_12_existing_gateway_authority_boundary_is_untouched(self):
        start = JS.index("function decisionContextPayload()")
        end = JS.index("function deviceLocation()", start)
        block = JS[start:end]
        for forbidden in ("ranking", "sponsor", "best_fit_candidate_id", "candidate_ids"):
            self.assertNotIn(forbidden, block)


if __name__ == "__main__":
    unittest.main()
