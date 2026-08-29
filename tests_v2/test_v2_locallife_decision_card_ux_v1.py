from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
APP = ROOT / "app.js"
CLIENT = ROOT / "js/core/locallife-api-client-v1.js"
EXECUTOR = ROOT / "js/core/locallife-action-executor-v1.js"
CARD = ROOT / "js/core/locallife-decision-card-v1.js"
STYLE = ROOT / "css/locallife-decision-card-v1.css"

class LocalLifeDecisionCardUXV1Tests(unittest.TestCase):
    def test_required_files_present(self):
        self.assertTrue(CARD.exists())
        self.assertTrue(STYLE.exists())

    def test_index_load_order_preserves_authority_boundaries(self):
        text = INDEX.read_text(encoding="utf-8")
        client = text.index("js/core/locallife-api-client-v1.js")
        executor = text.index("js/core/locallife-action-executor-v1.js")
        card = text.index("js/core/locallife-decision-card-v1.js")
        app = text.index("app.js?v=")
        self.assertLess(client, executor)
        self.assertLess(executor, card)
        self.assertLess(card, app)
        self.assertIn("css/locallife-decision-card-v1.css", text)

    def test_decision_card_uses_api_transport_not_direct_fetch(self):
        text = CARD.read_text(encoding="utf-8")
        self.assertIn("localLifeApiV1", text)
        self.assertIn(".decision(", text)
        self.assertNotIn("fetch(", text)
        self.assertIn("DECISION_TIMEOUT_MS = 90000", text)

    def test_browser_does_not_gain_ranking_authority(self):
        text = CARD.read_text(encoding="utf-8")
        for token in (".sort(", "decisionAssistant.recommend", "pilotBrainV0.build", "scoreCandidate", "rankingWeight"):
            self.assertNotIn(token, text)

    def test_user_action_execution_is_click_gated(self):
        text = CARD.read_text(encoding="utf-8")
        self.assertIn('button.addEventListener("click"', text)
        self.assertIn("executor.execute(action, { userConfirmed: true })", text)
        self.assertNotIn("executor.executeAll", text)

    def test_card_supports_generic_decision_states(self):
        text = CARD.read_text(encoding="utf-8")
        self.assertIn('status === "needs_user_input"', text)
        self.assertIn("best_fit_candidate_id", text)
        self.assertIn("uncertainty_fields", text)
        self.assertIn("MAX_ALTERNATIVES = 2", text)
        for action_type in ("OPEN_PLACE_CARD", "OPEN_MAP", "COMPARE_PLACES", "REQUEST_LOCATION"):
            self.assertIn(action_type, text)

    def test_legacy_search_path_is_still_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("performSearch", text)
        self.assertIn('"searchBtn"', text)

    def test_existing_transport_and_executor_remain_present(self):
        self.assertTrue(CLIENT.exists())
        self.assertTrue(EXECUTOR.exists())

if __name__ == "__main__":
    unittest.main()
