import unittest
from pathlib import Path

from place_platform_v2.semantic_conversation_understanding_v1 import (
    SemanticConversationStateV1,
    resolve_semantic_turn_v1,
)

ROOT = Path(__file__).resolve().parents[1]
SEM = (ROOT / "place_platform_v2/semantic_conversation_understanding_v1.py").read_text(encoding="utf-8")
BRAIN = (ROOT / "place_platform_v2/candidate_comparison_brain_v1.py").read_text(encoding="utf-8")
RUNTIME = (ROOT / "place_platform_v2/web_ai_runtime_v1.py").read_text(encoding="utf-8")
JS = (ROOT / "js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class T(unittest.TestCase):
    def state(self, **changes):
        base = dict(
            turn_index=4,
            active_request_text="หาร้านเจรังสิต",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
            candidate_ids=("A", "B", "C"),
        )
        base.update(changes)
        return SemanticConversationStateV1(**base)

    def test_01_generic_comparison_uses_prior_candidates(self):
        r = resolve_semantic_turn_v1(
            "ร้านไหนดีกว่า",
            {"conversation_state": self.state().to_payload()},
        )
        self.assertEqual("comparison", r.mode)
        self.assertEqual("overall", r.state.comparison_criterion)
        self.assertEqual(("A", "B", "C"), r.state.candidate_ids)

    def test_02_distance_comparison_preserves_candidates_and_requests_near_me(self):
        r = resolve_semantic_turn_v1(
            "ร้านไหนใกล้กว่า",
            {"conversation_state": self.state().to_payload()},
        )
        self.assertEqual("comparison", r.mode)
        self.assertEqual("distance", r.state.comparison_criterion)
        self.assertTrue(r.state.near_me)
        self.assertEqual(("A", "B", "C"), r.state.candidate_ids)

    def test_03_family_comparison_refines_same_candidate_set(self):
        r = resolve_semantic_turn_v1(
            "ถ้าพาแม่ไป ร้านไหนดีกว่า",
            {"conversation_state": self.state().to_payload()},
        )
        self.assertEqual("comparison", r.mode)
        self.assertIn("family", r.state.refinements)
        self.assertEqual(("A", "B", "C"), r.state.candidate_ids)

    def test_04_not_enough_candidates_fails_closed(self):
        r = resolve_semantic_turn_v1(
            "ร้านไหนดีกว่า",
            {"conversation_state": self.state(candidate_ids=("A",)).to_payload()},
        )
        self.assertEqual("comparison_unresolved", r.mode)

    def test_05_comparison_brain_calls_existing_dqe_path(self):
        self.assertIn("evaluate_published_decision(", BRAIN)
        self.assertNotIn(".sort(", BRAIN)
        self.assertNotIn("sorted(", BRAIN)

    def test_06_distance_is_a_dqe_preference_not_manual_sort(self):
        self.assertIn('ConsumerCondition(', BRAIN)
        self.assertIn('"distance_km"', BRAIN)
        self.assertIn('operator="lte"', BRAIN)
        self.assertIn("evaluate_published_decision(", BRAIN)

    def test_07_runtime_limits_comparison_to_prior_candidate_ids(self):
        self.assertIn("candidate_ids=state.candidate_ids", RUNTIME)
        self.assertIn("evaluate_prior_candidate_comparison_v1(", RUNTIME)

    def test_08_runtime_requires_location_for_distance_when_missing(self):
        block_start = RUNTIME.index("if comparison.needs_location:")
        block_end = RUNTIME.index("decision = comparison.decision", block_start)
        block = RUNTIME[block_start:block_end]
        self.assertIn('"current_location"', block)
        self.assertIn('"near_me"] = True', block)

    def test_09_runtime_exposes_candidate_names(self):
        self.assertIn('converted["candidate_summaries"]', RUNTIME)
        self.assertIn("def _candidate_summaries(", RUNTIME)

    def test_10_frontend_says_selected_candidate_name(self):
        self.assertIn("function recommendationRelay(result, bestId)", JS)
        self.assertIn("recommendationRelay(result, bestId)", JS)
        self.assertIn("ตัวเลือกแรก", JS)

    def test_11_frontend_renders_comparison_answer_before_generic_best_branch(self):
        compare = JS.index("const comparisonAnswer = String(")
        best = JS.index("const bestId = String(", compare)
        self.assertLess(compare, best)
        self.assertIn('addRobotMessage("assistant", comparisonAnswer);', JS[compare:best])

    def test_12_conversation_layer_does_not_rank_candidates(self):
        relay_start = JS.index("function recommendationRelay(")
        relay_end = JS.index("function unresolvedContextFields(", relay_start)
        block = JS[relay_start:relay_end]
        self.assertNotIn(".sort(", block)
        self.assertNotIn("score", block.casefold())

    def test_13_cache_bust(self):
        self.assertIn("comparison-candidate-awareness-v1", INDEX)


if __name__ == "__main__":
    unittest.main()
