import unittest
from dataclasses import dataclass

from place_platform_v2.end_to_end_real_decision_flow_v1 import (
    _candidate_compatible,
    _fetch_published_places,
)
from place_platform_v2.intent_context_understanding_v1 import understand_user_request
from place_platform_v2.semantic_conversation_understanding_v1 import (
    SemanticConversationStateV1,
    resolve_semantic_turn_v1,
)


def language_meaning(
    act="refine",
    *,
    category=None,
    decision_object=None,
    province=None,
    near_me=None,
):
    out = {
        "schema_version": "GENERIC-SEMANTIC-MEANING-V1",
        "confidence": 0.95,
        "conversation_act": act,
    }
    if category is not None:
        out["category"] = category
    if decision_object is not None:
        out["decision_object"] = decision_object
    if province is not None:
        out["province"] = province
    if near_me is not None:
        out["near_me"] = near_me
    return out


def prior_state():
    return SemanticConversationStateV1(
        turn_index=4,
        active_request_text="หาร้านเจในปราจีนบุรี",
        category="vegetarian",
        decision_object="restaurant",
        province="ปราจีนบุรี",
        candidate_ids=("veg-a", "veg-b", "veg-c"),
        last_user_text="หาร้านเจในปราจีนบุรี",
    )


@dataclass(frozen=True)
class FakePlace:
    place_id: str
    categories: tuple[str, ...]


class FakeRepo:
    def __init__(self, places):
        self.places = tuple(places)
        self.calls = 0

    def search_text(self, query):
        self.calls += 1
        return self.places

    def search_nearby(self, query):
        raise AssertionError("nearby not expected")


class TestWebAIConversationContextSwitchV1(unittest.TestCase):
    def test_01_cafe_switch_overrides_stale_vegetarian_state_and_keeps_province(self):
        s = prior_state()
        r = resolve_semantic_turn_v1(
            "แนะนำคาเฟ่",
            {"conversation_state": s.to_payload()},
            language_interpretation=language_meaning("refine"),
        )
        self.assertEqual("new_intent", r.mode)
        self.assertEqual("eat", r.state.category)
        self.assertEqual("restaurant", r.state.decision_object)
        self.assertEqual("ปราจีนบุรี", r.state.province)
        self.assertEqual((), r.state.candidate_ids)
        self.assertIn("คาเฟ่", r.effective_text)
        self.assertIn("ปราจีนบุรี", r.effective_text)

    def test_02_first_turn_language_new_request_keeps_cafe_word(self):
        r = resolve_semantic_turn_v1(
            "แนะนำคาเฟ่ในปราจีนบุรี",
            {},
            language_interpretation=language_meaning(
                "new_request",
                category="eat",
                decision_object="restaurant",
                province="ปราจีนบุรี",
                near_me=False,
            ),
        )
        self.assertEqual("new", r.mode)
        self.assertIn("คาเฟ่", r.effective_text)
        self.assertIn("ปราจีนบุรี", r.effective_text)

    def test_03_thai_difference_followup_is_comparison_even_if_provider_calls_it_refine(self):
        s = prior_state()
        r = resolve_semantic_turn_v1(
            "ต่างกันยังงัย",
            {"conversation_state": s.to_payload()},
            language_interpretation=language_meaning("refine"),
        )
        self.assertEqual("comparison", r.mode)
        self.assertEqual("overall", r.state.comparison_criterion)
        self.assertEqual(s.candidate_ids, r.state.candidate_ids)

    def test_04_nearest_followup_without_gwa_is_distance_comparison(self):
        s = prior_state()
        r = resolve_semantic_turn_v1(
            "ร้านไหนใกล้",
            {"conversation_state": s.to_payload()},
            language_interpretation=language_meaning("refine"),
        )
        self.assertEqual("comparison", r.mode)
        self.assertEqual("distance", r.state.comparison_criterion)
        self.assertTrue(r.state.near_me)
        self.assertEqual(s.candidate_ids, r.state.candidate_ids)

    def test_05_reference_fact_uses_prior_candidate_not_generic_recommendation(self):
        s = prior_state()
        r = resolve_semantic_turn_v1(
            "ร้านนี้อยู่ไหน",
            {"conversation_state": s.to_payload()},
            language_interpretation=language_meaning("refine"),
        )
        self.assertEqual("reference_fact", r.mode)
        self.assertEqual("address", r.state.reference_fact)
        self.assertEqual("veg-a", r.state.referenced_candidate_id)

    def test_06_ambiguous_new_recommendation_fails_closed_without_stale_candidates(self):
        s = prior_state()
        r = resolve_semantic_turn_v1(
            "แนะนำปิ้ง",
            {"conversation_state": s.to_payload()},
            language_interpretation=language_meaning("refine"),
        )
        self.assertEqual("language_clarification", r.mode)
        self.assertIsNone(r.state.category)
        self.assertIsNone(r.state.decision_object)
        self.assertEqual((), r.state.candidate_ids)
        self.assertEqual("ปราจีนบุรี", r.state.province)

    def test_07_explicit_cafe_request_filters_generic_restaurants(self):
        u = understand_user_request("แนะนำคาเฟ่ในปราจีนบุรี")
        generic = FakePlace("generic", ("eat", "restaurant"))
        cafe = FakePlace("cafe", ("eat", "cafe", "coffee"))
        self.assertFalse(_candidate_compatible(generic, u))
        self.assertTrue(_candidate_compatible(cafe, u))

    def test_08_cafe_subtype_is_prioritized_before_limit(self):
        u = understand_user_request("แนะนำคาเฟ่ในปราจีนบุรี")
        places = [
            FakePlace(f"generic-{i}", ("eat", "restaurant"))
            for i in range(100)
        ] + [FakePlace("cafe-last", ("eat", "cafe"))]
        repo = FakeRepo(places)
        result = _fetch_published_places(
            repo,
            u,
            origin=None,
            location_text=None,
            radius_km=20.0,
            limit=1,
        )
        self.assertEqual(1, repo.calls)
        self.assertEqual(("cafe-last",), tuple(x.place_id for x in result))

    def test_09_vegetarian_category_behavior_is_unchanged(self):
        # Pre-DQE compatibility is deliberately broad for restaurant objects.
        # Vegetarian exclusion remains a hard consumer/DQE constraint, already
        # covered by the exact real-query regression test.
        u = understand_user_request("หาร้านเจในปราจีนบุรี")
        veg = FakePlace("veg", ("vegetarian", "vegan"))
        generic = FakePlace("generic", ("eat", "restaurant"))
        self.assertTrue(_candidate_compatible(veg, u))
        self.assertTrue(_candidate_compatible(generic, u))
        hard = {(c.key, c.value, c.strength) for c in u.hard_constraints}
        self.assertIn(("vegetarian", True, "hard"), hard)


if __name__ == "__main__":
    unittest.main()
