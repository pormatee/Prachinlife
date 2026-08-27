from __future__ import annotations

import unittest

from place_platform_v2.master_super_brain_v1 import (
    DecisionCandidate,
    DecisionConstraint,
    DecisionPreference,
    DecisionRequest,
    EvidenceItem,
    evaluate_candidates,
)


def ev(field, value, status="verified", confidence=1.0, ref=None):
    return EvidenceItem(field, value, status, confidence, source_ref=ref)


class MasterSuperBrainV1Tests(unittest.TestCase):
    def test_hard_constraint_never_relaxed(self):
        request = DecisionRequest(
            "r1",
            "vegetarian dinner",
            category="vegetarian",
            constraints=(DecisionConstraint("vegetarian", "eq", True, "hard", 10),),
        )
        candidates = (
            DecisionCandidate("meat", "place", {"vegetarian": False}, (ev("vegetarian", False),)),
            DecisionCandidate("veg", "place", {"vegetarian": True}, (ev("vegetarian", True),)),
        )
        result = evaluate_candidates(request, candidates)
        self.assertEqual(result.recommended[0].candidate_id, "veg")
        self.assertNotIn("meat", [x.candidate_id for x in result.recommended])

    def test_all_hard_constraint_fail_returns_no_valid_candidate(self):
        request = DecisionRequest(
            "r2", "vegetarian",
            constraints=(DecisionConstraint("vegetarian", "eq", True, "hard", 1),),
        )
        result = evaluate_candidates(
            request,
            (DecisionCandidate("x", "place", {"vegetarian": False}, (ev("vegetarian", False),)),),
        )
        self.assertEqual(result.status, "no_valid_candidate")

    def test_provider_parity_same_brain_result(self):
        base = dict(
            request_id="r3",
            goal="nearby",
            preferences=(DecisionPreference("distance_norm", "prefer_low", 1),),
        )
        cands = (
            DecisionCandidate("a", "place", {"distance_norm": .2}, (ev("distance_norm", .2),)),
            DecisionCandidate("b", "place", {"distance_norm": .8}, (ev("distance_norm", .8),)),
        )
        a = evaluate_candidates(DecisionRequest(**base, provider="openai"), cands)
        b = evaluate_candidates(DecisionRequest(**base, provider="deepseek"), cands)
        self.assertEqual(
            [(x.candidate_id, x.organic_score) for x in a.recommended],
            [(x.candidate_id, x.organic_score) for x in b.recommended],
        )
        self.assertFalse(a.audit.provider_influenced_policy)
        self.assertFalse(b.audit.provider_influenced_policy)

    def test_sponsorship_never_changes_organic_ordering(self):
        request = DecisionRequest(
            "r4", "shopping",
            preferences=(DecisionPreference("distance_norm", "prefer_low", 1),),
        )
        common = {"distance_norm": .3}
        evidence = (ev("distance_norm", .3),)
        unsponsored = (
            DecisionCandidate("a", "branch", common, evidence, False),
            DecisionCandidate("b", "branch", common, evidence, False),
        )
        sponsored = (
            DecisionCandidate("a", "branch", common, evidence, False),
            DecisionCandidate("b", "branch", common, evidence, True),
        )
        r1 = evaluate_candidates(request, unsponsored)
        r2 = evaluate_candidates(request, sponsored)
        self.assertEqual(
            [(x.candidate_id, x.organic_score) for x in r1.recommended],
            [(x.candidate_id, x.organic_score) for x in r2.recommended],
        )

    def test_stale_evidence_is_explicit_and_reduces_confidence(self):
        request = DecisionRequest(
            "r5", "service",
            constraints=(DecisionConstraint("open_now", "eq", True, "soft", 1),),
        )
        stale = DecisionCandidate("s", "service", {"open_now": True}, (ev("open_now", True, "stale", .9),))
        fresh = DecisionCandidate("f", "service", {"open_now": True}, (ev("open_now", True, "verified", .9),))
        result = evaluate_candidates(request, (stale, fresh))
        by_id = {x.candidate_id: x for x in result.recommended}
        self.assertIn("open_now:stale", by_id["s"].uncertainties)
        self.assertLess(by_id["s"].evidence_confidence, by_id["f"].evidence_confidence)

    def test_regret_can_differ_from_upside(self):
        request = DecisionRequest(
            "r6", "trip",
            preferences=(DecisionPreference("excitement", "prefer_high", 1),),
            constraints=(DecisionConstraint("reliable", "eq", True, "soft", 1),),
        )
        high_upside = DecisionCandidate(
            "upside", "activity",
            {"excitement": 1.0, "reliable": True},
            (ev("excitement", 1.0, "verified", .95), ev("reliable", True, "stale", .3)),
        )
        safe = DecisionCandidate(
            "safe", "activity",
            {"excitement": .6, "reliable": True},
            (ev("excitement", .6, "verified", .95), ev("reliable", True, "verified", .95)),
        )
        result = evaluate_candidates(request, (high_upside, safe))
        self.assertEqual(result.upside_candidate_id, "upside")
        self.assertEqual(result.lower_regret_candidate_id, "safe")

    def test_reason_kinds_are_explicit(self):
        request = DecisionRequest(
            "r7", "eat",
            constraints=(DecisionConstraint("open_now", "eq", True, "soft", 1),),
        )
        result = evaluate_candidates(
            request,
            (DecisionCandidate("x", "place", {"open_now": True}, (ev("open_now", True, ref="e1"),)),),
        )
        self.assertTrue(result.recommended)
        self.assertEqual({r.kind for r in result.recommended[0].reasons}, {"fact", "inference"})

    def test_unknown_material_evidence_fails_closed_on_certainty(self):
        request = DecisionRequest(
            "r8", "need open place",
            constraints=(DecisionConstraint("open_now", "eq", True, "soft", 1),),
        )
        result = evaluate_candidates(
            request,
            (DecisionCandidate("x", "place", {"open_now": True}, ()),),
        )
        self.assertEqual(result.status, "insufficient_data")
        self.assertIn("open_now", result.missing_information)

    def test_human_always_decides(self):
        result = evaluate_candidates(
            DecisionRequest("r9", "explore"),
            (DecisionCandidate("x", "place", {}, ()),),
        )
        self.assertTrue(result.decision_boundary.human_decides)

    def test_provider_not_used_by_policy(self):
        request = DecisionRequest("r10", "explore", provider="anything")
        result = evaluate_candidates(request, (DecisionCandidate("x", "place", {}, ()),))
        self.assertFalse(result.audit.provider_influenced_policy)


if __name__ == "__main__":
    unittest.main()
