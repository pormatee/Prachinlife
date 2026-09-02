from pathlib import Path
import unittest
JS=Path("js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
CSS=Path("css/locallife-decision-card-v1.css").read_text(encoding="utf-8")
INDEX=Path("index.html").read_text(encoding="utf-8")
class T(unittest.TestCase):
    def test_top_feature(self):
        self.assertIn("ai-assistant-feature",JS)
        self.assertIn('document.getElementById("searchBtn")',JS)
        self.assertIn('searchRow.insertAdjacentElement("afterend", feature)',JS)
    def test_not_bottom_floating(self):
        self.assertIn("position: static !important",CSS)
        self.assertIn("display: none !important",CSS)
    def test_vector_robot(self):
        self.assertIn("modernRobotIcon",JS)
        self.assertIn("<svg",JS)
        self.assertIn("ai-assistant-mark",JS)
    def test_chat_readability_bounds(self):
        self.assertIn("max-height: 540px",CSS)
        self.assertIn("max-height: 380px",CSS)
    def test_search_independent(self):
        i=JS.index("async function requestDecision")
        self.assertNotIn('document.getElementById("searchInput")',JS[i:i+1000])
        self.assertIn('document.getElementById("robotAssistInput")',JS[i:i+1000])
    def test_recommend_then_one_question(self):
        self.assertIn("result?.highest_value_question",JS)
        self.assertIn("robotAssistPendingBaseQuery = decisionText",JS)
    def test_refinement(self):
        self.assertIn("ข้อมูลเพิ่มเติมจากผู้ใช้:",JS)
        self.assertIn("text: decisionText",JS)
    def test_result_area_reused(self):
        self.assertIn("localLifeDecisionCardSection",JS)
        self.assertIn("scrollIntoView",JS)
    def test_decision_card_script_is_versioned(self):
        self.assertIn("js/core/locallife-decision-card-v1.js?v=",INDEX)
if __name__=="__main__": unittest.main()
