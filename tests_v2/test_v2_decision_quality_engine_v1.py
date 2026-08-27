from __future__ import annotations
import unittest

from place_platform_v2.master_super_brain_v1 import (
    DecisionCandidate, DecisionConstraint, DecisionPreference,
    DecisionRequest, EvidenceItem,
)
from place_platform_v2.decision_quality_engine_v1 import evaluate_decision_quality


def ev(field, value, status="verified", confidence=1.0, ref=None):
    return EvidenceItem(field, value, status, confidence, source_ref=ref)


class DecisionQualityEngineV1Tests(unittest.TestCase):

    def test_vegetarian_hard_constraint(self):
        req = DecisionRequest(
            "veg-1", "find vegetarian dinner", category="vegetarian",
            constraints=(DecisionConstraint("vegetarian", "eq", True, "hard", 10),),
            preferences=(DecisionPreference("distance_norm", "prefer_low", 1),),
        )
        cands = (
            DecisionCandidate("bad", "place",
                {"vegetarian": False, "distance_norm": .1, "open_now": True},
                (ev("vegetarian", False), ev("distance_norm", .1), ev("open_now", True))),
            DecisionCandidate("good", "place",
                {"vegetarian": True, "distance_norm": .4, "open_now": True},
                (ev("vegetarian", True), ev("distance_norm", .4), ev("open_now", True))),
        )
        r = evaluate_decision_quality(req, cands)
        self.assertEqual([x.candidate_id for x in r.recommended], ["good"])

    def test_nearer_but_stale_can_lose_to_farther_reliable(self):
        req = DecisionRequest(
            "eat-1", "eat nearby without risking closed shop", category="eat",
            constraints=(DecisionConstraint("open_now", "eq", True, "soft", 5),),
            preferences=(DecisionPreference("distance_norm", "prefer_low", 2),),
        )
        near = DecisionCandidate(
            "near", "place",
            {"open_now": True, "distance_norm": .1, "diet_match": 1.0},
            (ev("open_now", True, "stale", .5), ev("distance_norm", .1), ev("diet_match", 1.0)),
        )
        reliable = DecisionCandidate(
            "reliable", "place",
            {"open_now": True, "distance_norm": .4, "diet_match": 1.0},
            (ev("open_now", True, "verified", .95), ev("distance_norm", .4), ev("diet_match", 1.0)),
        )
        r = evaluate_decision_quality(req, (near, reliable))
        self.assertEqual(r.lower_regret_candidate_id, "reliable")
        self.assertEqual(r.recommended[0].candidate_id, "reliable")
        by = {x.candidate_id: x for x in r.recommended}
        self.assertIn("open_now:stale", by["near"].uncertainties)

    def test_shopping_stock_uncertainty_has_high_regret(self):
        req = DecisionRequest(
            "shop-1", "buy item today", category="shopping",
            constraints=(DecisionConstraint("in_stock", "eq", True, "soft", 5),),
            preferences=(DecisionPreference("price_norm", "prefer_low", 1),),
        )
        cheap_unknown = DecisionCandidate(
            "cheap", "branch",
            {"in_stock": True, "price_norm": .1, "distance_norm": .2},
            (ev("in_stock", True, "unknown", 0), ev("price_norm", .1), ev("distance_norm", .2)),
        )
        normal_verified = DecisionCandidate(
            "normal", "branch",
            {"in_stock": True, "price_norm": .4, "distance_norm": .3},
            (ev("in_stock", True, "verified", .95), ev("price_norm", .4), ev("distance_norm", .3)),
        )
        r = evaluate_decision_quality(req, (cheap_unknown, normal_verified))
        self.assertEqual(r.lower_regret_candidate_id, "normal")
        self.assertGreater(
            {x.candidate_id:x for x in r.recommended}["cheap"].regret_risk,
            {x.candidate_id:x for x in r.recommended}["normal"].regret_risk,
        )

    def test_go_upside_and_lower_regret_can_differ(self):
        req = DecisionRequest(
            "go-1", "choose outing", category="go",
            preferences=(DecisionPreference("excitement", "prefer_high", 3),),
        )
        exciting = DecisionCandidate(
            "exciting", "activity",
            {"excitement": 1.0, "open_now": True, "weather_fit": 1.0, "travel_time_norm": .2},
            (ev("excitement",1), ev("open_now",True,"stale",.4), ev("weather_fit",1,"stale",.4), ev("travel_time_norm",.2)),
        )
        safe = DecisionCandidate(
            "safe", "activity",
            {"excitement": .65, "open_now": True, "weather_fit": 1.0, "travel_time_norm": .3},
            (ev("excitement",.65), ev("open_now",True), ev("weather_fit",1), ev("travel_time_norm",.3)),
        )
        r = evaluate_decision_quality(req, (exciting, safe))
        self.assertEqual(r.upside_candidate_id, "exciting")
        self.assertEqual(r.lower_regret_candidate_id, "safe")

    def test_service_capability_and_availability_are_material(self):
        req = DecisionRequest(
            "svc-1", "need service now", category="service",
            constraints=(
                DecisionConstraint("available_now", "eq", True, "soft", 4),
                DecisionConstraint("capability_match", "eq", True, "hard", 10),
            ),
        )
        wrong = DecisionCandidate(
            "wrong", "service",
            {"available_now": True, "capability_match": False, "distance_norm": .1},
            (ev("available_now", True), ev("capability_match",False), ev("distance_norm",.1)),
        )
        right = DecisionCandidate(
            "right", "service",
            {"available_now": True, "capability_match": True, "distance_norm": .5},
            (ev("available_now", True), ev("capability_match",True), ev("distance_norm",.5)),
        )
        r = evaluate_decision_quality(req, (wrong, right))
        self.assertEqual([x.candidate_id for x in r.recommended], ["right"])

    def test_sponsor_does_not_change_decision(self):
        req = DecisionRequest(
            "sponsor-1", "shopping", category="shopping",
            preferences=(DecisionPreference("price_norm", "prefer_low", 1),),
        )
        attrs = {"in_stock": True, "price_norm": .3, "distance_norm": .2}
        evidence = (ev("in_stock",True), ev("price_norm",.3), ev("distance_norm",.2))
        a = DecisionCandidate("a","branch",attrs,evidence,False)
        b1 = DecisionCandidate("b","branch",attrs,evidence,False)
        b2 = DecisionCandidate("b","branch",attrs,evidence,True)
        r1 = evaluate_decision_quality(req,(a,b1))
        r2 = evaluate_decision_quality(req,(a,b2))
        self.assertEqual(
            [(x.candidate_id,x.organic_score) for x in r1.recommended],
            [(x.candidate_id,x.organic_score) for x in r2.recommended],
        )

    def test_provider_metadata_does_not_change_result(self):
        common = dict(
            request_id="provider-1", goal="compare", category="eat",
            preferences=(DecisionPreference("distance_norm","prefer_low",1),),
        )
        cands = (
            DecisionCandidate("a","place",{"distance_norm":.2,"open_now":True,"diet_match":1},
                (ev("distance_norm",.2),ev("open_now",True),ev("diet_match",1))),
            DecisionCandidate("b","place",{"distance_norm":.5,"open_now":True,"diet_match":1},
                (ev("distance_norm",.5),ev("open_now",True),ev("diet_match",1))),
        )
        r1 = evaluate_decision_quality(DecisionRequest(**common, provider="openai"), cands)
        r2 = evaluate_decision_quality(DecisionRequest(**common, provider="deepseek"), cands)
        self.assertEqual(
            [(x.candidate_id,x.organic_score,x.regret_risk) for x in r1.recommended],
            [(x.candidate_id,x.organic_score,x.regret_risk) for x in r2.recommended],
        )
        self.assertFalse(r1.audit.provider_influenced_policy)

    def test_unknown_material_fields_fail_closed(self):
        req = DecisionRequest("unknown-1","eat",category="eat")
        cand = DecisionCandidate("x","place",{"open_now":True,"distance_norm":.2,"diet_match":1},())
        r = evaluate_decision_quality(req,(cand,))
        self.assertEqual(r.status,"insufficient_data")
        self.assertTrue(r.missing_information)
        self.assertTrue(r.decision_boundary.human_decides)


if __name__ == "__main__":
    unittest.main()
