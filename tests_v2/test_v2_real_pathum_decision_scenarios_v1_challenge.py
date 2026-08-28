from __future__ import annotations
import unittest

from place_platform_v2.real_pathum_decision_scenarios_v1 import (
    PATHUM_LABELS,
    SCENARIO_FACT_PREFIX,
    build_pathum_scenario_repository,
    run_real_pathum_scenario_v1,
    scenario_fact,
)
from place_platform_v2.contextual_personal_decision_v1 import DecisionTimeFact
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.read_model import PublishedNearbyQuery, PublishedTextQuery


class RealPathumDecisionScenariosV1ChallengeTest(unittest.TestCase):
    def test_01_cross_candidate_fact_cannot_satisfy_other_candidate(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c01",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                scenario_fact("vegan-garden","open_now",True),
                scenario_fact("baanj","open_now",False),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"vegan-garden")

    def test_02_conflicting_open_now_is_unresolved(self):
        facts=(
            scenario_fact("baanj","open_now",True,state="conflicting"),
            scenario_fact("vegan-garden","open_now",False),
            scenario_fact("so-vegan-aiyara","open_now",False),
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="c02",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=facts,
        )
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIn("baanj",out.decision.unresolved_candidate_ids)

    def test_03_unknown_open_now_is_unresolved(self):
        facts=(
            scenario_fact("baanj","open_now",True,state="unknown"),
            scenario_fact("vegan-garden","open_now",False),
            scenario_fact("so-vegan-aiyara","open_now",False),
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="c03",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=facts,
        )
        self.assertIsNone(out.decision.best_fit_candidate_id)

    def test_04_missing_open_for_one_candidate_does_not_borrow_true_from_another(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c04",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                scenario_fact("vegan-garden","open_now",True),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"vegan-garden")
        self.assertIn("baanj",out.decision.unresolved_candidate_ids)

    def test_05_missing_price_under_hard_cap_is_not_assumed_affordable(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c05",
            user_text="หาร้านเจปทุมธานี",
            context={"budget_max":100},
            decision_time_facts=(
                scenario_fact("baanj","price_amount",80),
                scenario_fact("vegan-garden","price_amount",120),
            ),
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        self.assertIn("so-vegan-aiyara",out.decision.unresolved_candidate_ids)

    def test_06_stale_price_under_hard_cap_is_unresolved_not_satisfied(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c06",
            user_text="หาร้านเจปทุมธานี",
            context={"budget_max":100},
            decision_time_facts=(
                scenario_fact("baanj","price_amount",80,state="stale"),
                scenario_fact("vegan-garden","price_amount",120),
                scenario_fact("so-vegan-aiyara","price_amount",130),
            ),
        )
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIn("baanj",out.decision.unresolved_candidate_ids)

    def test_07_novelty_history_cannot_invent_unknown_candidate(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c07",
            user_text="หาร้านเจปทุมธานี อยากลองร้านใหม่",
            visited_candidate_ids=("not-a-real-candidate",),
        )
        self.assertIn(out.decision.best_fit_candidate_id, PATHUM_LABELS)
        self.assertNotEqual(out.decision.best_fit_candidate_id,"not-a-real-candidate")

    def test_08_near_me_radius_excludes_farther_scenario_candidates(self):
        repo=build_pathum_scenario_repository()
        nearby=repo.search_nearby(PublishedNearbyQuery(
            origin=GeoPoint(14.076182,100.633498),
            radius_km=0.2,
            province="ปทุมธานี",
            limit=20,
        ))
        nearby_ids=tuple(x.place.place_id for x in nearby)
        self.assertEqual(nearby_ids,("baanj",))

        out=run_real_pathum_scenario_v1(
            scenario_id="c08",
            user_text="หาร้านเจใกล้ฉัน",
            context={"current_location":(14.076182,100.633498)},
            radius_km=0.2,
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        presented_ids=tuple(
            [out.presentation.recommendation.candidate_id]
            if out.presentation.recommendation is not None else []
        ) + tuple(x.candidate_id for x in out.presentation.alternatives)
        self.assertNotIn("vegan-garden",presented_ids)
        self.assertNotIn("so-vegan-aiyara",presented_ids)

    def test_09_typo_pathum_and_vegetarian_semantics_preserved(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c09",
            user_text="หาร้านมังสะวิรัติ ปทุมทานี",
        )
        self.assertFalse(out.decision.needs_user_input)
        self.assertIn(out.decision.best_fit_candidate_id,PATHUM_LABELS)
        self.assertEqual(out.decision.understanding.province,"ปทุมธานี")

    def test_10_unknown_intent_with_context_still_fails_closed(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c10",
            user_text="เอาที่โอเคก็ได้",
            context={"current_location":(14.076182,100.633498)},
        )
        self.assertTrue(out.decision.needs_user_input)
        self.assertIsNone(out.presentation.recommendation)

    def test_11_untrusted_fact_source_text_does_not_gain_ranking_authority(self):
        fact=DecisionTimeFact(
            place_id="baanj",
            field="open_now",
            value=True,
            state="verified",
            source_ref="sponsor:paid-placement",
            observed_at="2026-08-28T19:00:00+07:00",
            confidence=1.0,
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="c11",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                fact,
                scenario_fact("vegan-garden","open_now",False),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        self.assertEqual(out.presentation.recommendation.candidate_id,"baanj")

    def test_12_presenter_label_cannot_change_candidate_identity(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c12",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                scenario_fact("baanj","open_now",True),
                scenario_fact("vegan-garden","open_now",False),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertEqual(out.presentation.recommendation.candidate_id,
                         out.decision.best_fit_candidate_id)

    def test_13_scenario_repo_contains_only_pathum_province(self):
        repo=build_pathum_scenario_repository()
        rows=repo.search_text(PublishedTextQuery(
            text="",
            province="ปทุมธานี",
            limit=20,
        ))
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r.province=="ปทุมธานี" for r in rows))

    def test_14_recognized_wrong_province_query_does_not_leak_pathum_candidates(self):
        # ICU V1.2 recognizes ชลบุรี, so this exercises the frozen province
        # scope contract rather than an unsupported province-name case.
        out=run_real_pathum_scenario_v1(
            scenario_id="c14",
            user_text="หาร้านเจชลบุรี",
        )
        self.assertEqual(out.decision.understanding.province,"ชลบุรี")
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIsNone(out.presentation.recommendation)

    def test_15_dynamic_fact_refs_are_candidate_scoped(self):
        facts=(
            scenario_fact("baanj","open_now",True),
            scenario_fact("vegan-garden","open_now",False),
        )
        self.assertTrue(facts[0].source_ref.startswith(SCENARIO_FACT_PREFIX+"baanj:"))
        self.assertTrue(facts[1].source_ref.startswith(SCENARIO_FACT_PREFIX+"vegan-garden:"))

    def test_16_no_dynamic_facts_are_claimed_live_by_harness_contract(self):
        fact=scenario_fact("baanj","parking",True)
        self.assertTrue(fact.source_ref.startswith(SCENARIO_FACT_PREFIX))
        self.assertNotIn("live:",fact.source_ref.lower())

    def test_17_fail_closed_presentation_keeps_human_boundary(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c17",
            user_text="หาร้านเจใกล้ฉัน",
        )
        self.assertIsNone(out.presentation.recommendation)
        self.assertTrue(out.presentation.human_final_decision)
        self.assertIn("ผู้ใช้เป็นผู้ตัดสินใจสุดท้าย",out.presentation.human_boundary)

    def test_18_success_presentation_keeps_human_boundary(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="c18",
            user_text="หาร้านเจปทุมธานี",
        )
        self.assertIsNotNone(out.presentation.recommendation)
        self.assertTrue(out.presentation.human_final_decision)

if __name__=="__main__":
    unittest.main()
