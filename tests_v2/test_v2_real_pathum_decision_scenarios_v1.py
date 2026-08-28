from __future__ import annotations
import unittest

from place_platform_v2.real_pathum_decision_scenarios_v1 import (
    PATHUM_LABELS,
    SCENARIO_FACT_PREFIX,
    run_real_pathum_scenario_v1,
    scenario_fact,
)


class RealPathumDecisionScenariosV1Test(unittest.TestCase):
    def test_01_near_me_without_location_never_ranks(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p01",
            user_text="หาร้านเจใกล้ฉัน",
        )
        self.assertTrue(out.decision.needs_user_input)
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIsNone(out.presentation.recommendation)
        self.assertEqual(out.presentation.presentation_status,"needs_user_input")

    def test_02_near_me_with_location_uses_pathum_published_candidates(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p02",
            user_text="หาร้านเจใกล้ฉัน",
            context={"current_location":(14.0762,100.6335)},
            radius_km=3.0,
        )
        self.assertFalse(out.decision.needs_user_input)
        self.assertIsNotNone(out.decision.best_fit_candidate_id)
        self.assertIn(out.decision.best_fit_candidate_id,PATHUM_LABELS)
        self.assertIsNotNone(out.presentation.recommendation)

    def test_03_now_requires_decision_time_open_evidence(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p03",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                scenario_fact("baanj","open_now",True),
                scenario_fact("vegan-garden","open_now",False),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        self.assertIn("vegan-garden",out.decision.rejected_candidate_ids)
        self.assertEqual(out.presentation.recommendation.display_name,PATHUM_LABELS["baanj"])

    def test_04_now_with_missing_open_evidence_fails_closed_for_that_candidate(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p04",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                scenario_fact("vegan-garden","open_now",False),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIn("baanj",out.decision.unresolved_candidate_ids)
        self.assertIn("open_now",out.decision.uncertainty_fields)
        self.assertIsNone(out.presentation.recommendation)

    def test_05_stale_open_fact_is_not_treated_as_current_truth(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p05",
            user_text="หาร้านเจปทุมธานีตอนนี้",
            decision_time_facts=(
                scenario_fact("baanj","open_now",True,state="stale",confidence=0.5),
                scenario_fact("vegan-garden","open_now",False),
                scenario_fact("so-vegan-aiyara","open_now",False),
            ),
        )
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIn("baanj",out.decision.unresolved_candidate_ids)

    def test_06_family_context_prefers_family_suitability_and_parking(self):
        facts=(
            scenario_fact("baanj","family_suitability",True),
            scenario_fact("baanj","parking",True),
            scenario_fact("vegan-garden","family_suitability",False),
            scenario_fact("vegan-garden","parking",False),
            scenario_fact("so-vegan-aiyara","family_suitability",False),
            scenario_fact("so-vegan-aiyara","parking",False),
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="p06",
            user_text="หาร้านเจปทุมธานี ไปกับลูก",
            decision_time_facts=facts,
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        self.assertIn("family_prefers_suitability_and_parking",out.decision.profile.applied_rules)

    def test_07_budget_sensitive_context_prefers_lower_normalized_price(self):
        facts=(
            scenario_fact("baanj","price",0.25),
            scenario_fact("vegan-garden","price",0.55),
            scenario_fact("so-vegan-aiyara","price",0.85),
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="p07",
            user_text="หาร้านเจปทุมธานี ปลายเดือนแล้ว",
            decision_time_facts=facts,
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        self.assertIn("budget_prefers_lower_price",out.decision.profile.applied_rules)

    def test_08_explicit_budget_cap_rejects_over_budget_and_unresolved_missing_price(self):
        facts=(
            scenario_fact("baanj","price_amount",90),
            scenario_fact("vegan-garden","price_amount",150),
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="p08",
            user_text="หาร้านเจปทุมธานี",
            context={"budget_max":100},
            decision_time_facts=facts,
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"baanj")
        self.assertIn("vegan-garden",out.decision.rejected_candidate_ids)
        self.assertIn("so-vegan-aiyara",out.decision.unresolved_candidate_ids)

    def test_09_novelty_uses_only_explicit_trusted_visit_history(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p09",
            user_text="หาร้านเจปทุมธานี อยากลองร้านใหม่",
            visited_candidate_ids=("baanj","vegan-garden"),
        )
        self.assertEqual(out.decision.best_fit_candidate_id,"so-vegan-aiyara")
        self.assertIn("user-context:visited-history",out.decision.applied_fact_refs)

    def test_10_novelty_without_history_remains_uncertain_not_invented(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p10",
            user_text="หาร้านเจปทุมธานี อยากลองร้านใหม่",
        )
        self.assertIn("novelty",out.decision.uncertainty_fields)

    def test_11_presenter_preserves_decision_and_exposes_uncertainty(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p11",
            user_text="หาร้านเจราคาประหยัดปทุมธานี",
        )
        self.assertEqual(
            None if out.presentation.recommendation is None else out.presentation.recommendation.candidate_id,
            out.decision.best_fit_candidate_id,
        )
        self.assertIn("price",out.decision.uncertainty_fields)
        self.assertIn("price",out.presentation.uncertainty_items)

    def test_12_all_dynamic_scenario_evidence_has_explicit_scenario_provenance(self):
        facts=(
            scenario_fact("baanj","open_now",True),
            scenario_fact("baanj","price",0.25),
        )
        out=run_real_pathum_scenario_v1(
            scenario_id="p12",
            user_text="หาร้านเจปทุมธานีตอนนี้ ปลายเดือน",
            decision_time_facts=facts,
        )
        self.assertTrue(out.decision.applied_fact_refs)
        self.assertTrue(all(ref.startswith(SCENARIO_FACT_PREFIX) for ref in out.decision.applied_fact_refs))

    def test_13_unknown_intent_does_not_use_pathum_fixture_to_guess(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p13",
            user_text="ช่วยเลือกอะไรสักอย่างให้หน่อย",
        )
        self.assertTrue(out.decision.needs_user_input)
        self.assertIsNone(out.decision.best_fit_candidate_id)
        self.assertIsNone(out.presentation.recommendation)

    def test_14_human_final_decision_survives_full_pathum_chain(self):
        out=run_real_pathum_scenario_v1(
            scenario_id="p14",
            user_text="หาร้านเจปทุมธานี",
        )
        self.assertTrue(out.decision.human_final_decision)
        self.assertTrue(out.presentation.human_final_decision)
        self.assertIn("ผู้ใช้เป็นผู้ตัดสินใจสุดท้าย",out.presentation.human_boundary)


if __name__=="__main__":
    unittest.main()
