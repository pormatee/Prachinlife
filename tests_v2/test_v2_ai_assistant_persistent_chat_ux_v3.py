from pathlib import Path
import unittest

JS=Path("js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
INDEX=Path("index.html").read_text(encoding="utf-8")

class TestPersistentChatUxV3(unittest.TestCase):
    def test_chat_remains_open_after_best_fit(self):
        i=JS.index("if (bestId)")
        block=JS[i:i+1500]
        self.assertIn("openRobotAssist();", block)
        self.assertNotIn('robotAssistPendingBaseQuery = "";\n          closeRobotAssist();', block)

    def test_followup_question_kept(self):
        self.assertIn("result?.highest_value_question", JS)
        self.assertIn("robotAssistPendingBaseQuery = decisionText", JS)

    def test_detail_click_collapses(self):
        self.assertIn("function bindDetailCollapse()", JS)
        self.assertIn(".place-card-action-detail", JS)
        self.assertIn("OPEN_PLACE_CARD", JS)
        self.assertIn("closeRobotAssist();", JS)

    def test_action_type_tag(self):
        self.assertIn("button.dataset.actionType", JS)

    def test_chat_not_destroyed(self):
        i=JS.index("function bindDetailCollapse()")
        block=JS[i:i+1200]
        self.assertNotIn("replaceChildren", block)
        self.assertNotIn("remove()", block)

    def test_search_stays_separate(self):
        i=JS.index("async function requestDecision")
        self.assertIn('document.getElementById("robotAssistInput")', JS[i:i+1000])
        self.assertNotIn('document.getElementById("searchInput")', JS[i:i+1000])

    def test_cache_bust(self):
        self.assertIn("ai-assistant-persistent-chat-ux-v3", INDEX)

if __name__=="__main__":
    unittest.main()
