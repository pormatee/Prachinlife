from pathlib import Path
import unittest
JS=Path("js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
CSS=Path("css/locallife-decision-card-v1.css").read_text(encoding="utf-8")
INDEX=Path("index.html").read_text(encoding="utf-8")
class T(unittest.TestCase):
    def test_separate_input(self):
        self.assertIn('document.getElementById("robotAssistInput")',JS)
        i=JS.index("async function requestDecision")
        self.assertNotIn('document.getElementById("searchInput")',JS[i:i+700])
    def test_assistant_remains_separate_from_search(self):
        self.assertIn("createRobotPanel",JS)
        self.assertIn("ai-assistant-feature",JS)
        self.assertNotIn('searchButton.insertAdjacentElement("afterend", button)',JS)
    def test_compact_panel(self):
        self.assertIn("max-height: min(38vh, 340px)",CSS)
        self.assertIn("robot-assist-panel",CSS)
    def test_result_area_reused(self):
        self.assertIn("localLifeDecisionCardSection",JS)
        self.assertIn("renderResponse(response)",JS)
        self.assertIn("scrollIntoView",JS)
    def test_decision_card_script_is_versioned(self):
        self.assertIn("js/core/locallife-decision-card-v1.js?v=",INDEX)
if __name__=="__main__": unittest.main()
