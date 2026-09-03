import unittest
from pathlib import Path

from place_platform_v2.semantic_conversation_understanding_v1 import (
    SEMANTIC_CONVERSATION_STATE_VERSION,
    SemanticConversationStateV1,
    finalize_semantic_state_v1,
    resolve_semantic_turn_v1,
    state_from_payload,
)


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class TestSemanticConversationalUnderstandingV1(unittest.TestCase):
    def test_01_first_turn_preserves_original_text_and_builds_state(self):
        r = resolve_semantic_turn_v1(
            "หาร้านเจใกล้ฉัน",
            {"current_location": [14.0, 100.0]},
        )
        self.assertEqual("หาร้านเจใกล้ฉัน", r.effective_text)
        self.assertEqual("vegetarian", r.state.category)
        self.assertEqual("restaurant", r.state.decision_object)
        self.assertTrue(r.state.near_me)
        self.assertEqual(1, r.state.turn_index)
        self.assertNotIn("conversation_state", r.brain_context)

    def test_02_budget_followup_refines_existing_intent_without_text_history(self):
        s = SemanticConversationStateV1(
            turn_index=1,
            active_request_text="หาร้านเจใกล้ฉัน",
            category="vegetarian",
            decision_object="restaurant",
            near_me=True,
        )
        r = resolve_semantic_turn_v1(
            "เอาไม่แพง",
            {"current_location": [14.0, 100.0], "conversation_state": s.to_payload()},
        )
        self.assertEqual("refine", r.mode)
        self.assertIn("หาร้านเจ", r.effective_text)
        self.assertIn("ใกล้ฉัน", r.effective_text)
        self.assertIn("ราคาไม่แพง", r.effective_text)
        self.assertEqual(("budget_sensitive",), r.state.refinements)
        self.assertNotIn("หาร้านเจใกล้ฉัน\n", r.effective_text)

    def test_03_old_location_text_does_not_turn_budget_followup_into_location_change(self):
        s = SemanticConversationStateV1(
            turn_index=2,
            active_request_text="หาร้านเจ",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
        )
        r = resolve_semantic_turn_v1(
            "เอาไม่แพง",
            {"location_text": "รังสิต", "conversation_state": s.to_payload()},
        )
        self.assertEqual("refine", r.mode)
        self.assertEqual("ปทุมธานี", r.state.province)
        self.assertEqual("รังสิต", r.brain_context["location_text"])

    def test_04_explicit_location_change_replaces_old_province(self):
        s = SemanticConversationStateV1(
            turn_index=2,
            active_request_text="หาร้านเจ",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
        )
        r = resolve_semantic_turn_v1(
            "เปลี่ยนเป็นปราจีนบุรี",
            {"location_text": "รังสิต", "conversation_state": s.to_payload()},
        )
        self.assertEqual("location_change", r.mode)
        self.assertEqual("ปราจีนบุรี", r.state.province)
        self.assertIn("ปราจีนบุรี", r.effective_text)
        self.assertNotIn("ปทุมธานี", r.effective_text)
        self.assertEqual("เปลี่ยนเป็นปราจีนบุรี", r.brain_context["location_text"])

    def test_05_parking_and_family_refinements_accumulate(self):
        s = SemanticConversationStateV1(
            turn_index=1,
            active_request_text="หาร้านเจ",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
            refinements=("parking",),
        )
        r = resolve_semantic_turn_v1(
            "ถ้าพาแม่ไปล่ะ",
            {"conversation_state": s.to_payload()},
        )
        self.assertEqual(("parking", "family"), r.state.refinements)
        self.assertIn("มีที่จอดรถ", r.effective_text)
        self.assertIn("เหมาะกับครอบครัว", r.effective_text)

    def test_06_reference_resolution_uses_brain_supplied_candidate_order_only(self):
        s = SemanticConversationStateV1(
            turn_index=3,
            active_request_text="หาร้านเจ",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
            candidate_ids=("A", "B", "C"),
        )
        r = resolve_semantic_turn_v1(
            "ร้านที่สอง",
            {"conversation_state": s.to_payload()},
        )
        self.assertEqual("reference", r.mode)
        self.assertEqual("B", r.state.referenced_candidate_id)
        self.assertNotIn("referenced_candidate_id", r.brain_context)

    def test_07_brain_result_is_only_source_of_candidate_identity_order(self):
        s = SemanticConversationStateV1(
            turn_index=2,
            category="vegetarian",
            decision_object="restaurant",
        )
        result = {
            "understanding": {"category": "vegetarian", "decision_object": "restaurant", "province": "ปทุมธานี", "near_me": False},
            "explanation": {"best_fit_candidate_id": "B", "alternatives": ["C", "A"]},
        }
        final = finalize_semantic_state_v1(s, result)
        self.assertEqual(("B", "C", "A"), final.candidate_ids)

    def test_08_new_category_resets_old_refinements_and_candidates(self):
        s = SemanticConversationStateV1(
            turn_index=4,
            active_request_text="หาร้านเจ",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
            refinements=("budget_sensitive", "parking"),
            candidate_ids=("A", "B", "C"),
        )
        r = resolve_semantic_turn_v1(
            "เที่ยวปราจีนบุรีไหนดี",
            {"conversation_state": s.to_payload()},
        )
        self.assertEqual("new_intent", r.mode)
        self.assertEqual("go", r.state.category)
        self.assertEqual((), r.state.refinements)
        self.assertEqual((), r.state.candidate_ids)
        self.assertIn("ปราจีนบุรี", r.effective_text)

    def test_09_state_payload_has_no_gps_provider_sponsor_or_ranking_authority(self):
        payload = SemanticConversationStateV1().to_payload()
        forbidden = {
            "current_location", "latitude", "longitude", "coordinates",
            "provider", "sponsor", "sponsor_score", "ranking", "rank", "score",
        }
        self.assertTrue(forbidden.isdisjoint(payload.keys()))

    def test_10_state_validation_is_fail_closed(self):
        with self.assertRaises(ValueError):
            state_from_payload({"schema_version": "WRONG"})
        with self.assertRaises(ValueError):
            state_from_payload({"schema_version": SEMANTIC_CONVERSATION_STATE_VERSION, "turn_index": "2"})

    def test_11_candidate_reference_is_invalidated_when_candidate_set_changes(self):
        s = SemanticConversationStateV1(
            candidate_ids=("A", "B", "C"),
            referenced_candidate_id="B",
        )
        result = {
            "understanding": {},
            "explanation": {"best_fit_candidate_id": "X", "alternatives": ["Y"]},
        }
        final = finalize_semantic_state_v1(s, result)
        self.assertEqual(("X", "Y"), final.candidate_ids)
        self.assertIsNone(final.referenced_candidate_id)


    def test_12_frontend_persists_and_forwards_server_issued_semantic_state(self):
        self.assertIn("let robotAssistSemanticState = null;", JS)
        self.assertIn("semantic_state: normalizedSemanticState(robotAssistSemanticState)", JS)
        self.assertIn("payload.conversation_state = semanticState", JS)
        self.assertIn("captureSemanticState(result);", JS)

    def test_13_decision_path_no_longer_concatenates_free_text_history(self):
        start = JS.index("function conversationDecisionText(query, pendingWasStructured)")
        end = JS.index("function resetConversationState()", start)
        block = JS[start:end]
        self.assertNotIn("บริบทจากข้อความผู้ใช้ก่อนหน้า:", block)
        self.assertNotIn("previousTurns", block)
        self.assertIn("return latest;", block)

    def test_14_semantic_state_does_not_persist_exact_device_coordinates(self):
        start = JS.index("function normalizedSemanticState(raw)")
        end = JS.index("function captureSemanticState(result)", start)
        block = JS[start:end]
        self.assertNotIn("current_location", block)
        self.assertNotIn("latitude", block)
        self.assertNotIn("longitude", block)

    def test_15_semantic_frontend_cache_is_busted(self):
        self.assertIn("semantic-conversation-understanding-v1", INDEX)


if __name__ == "__main__":
    unittest.main()
