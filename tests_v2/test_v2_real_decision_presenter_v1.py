from __future__ import annotations

from dataclasses import dataclass
import unittest

from place_platform_v2.real_decision_presenter_v1 import (
    PRESENTER_POLICY_VERSION,
    present_contextual_personal_decision_v1,
    present_end_to_end_decision_v1,
)


@dataclass(frozen=True)
class FakeExplanation:
    best_fit_candidate_id: str | None = None
    best_fit_name: str | None = None
    alternatives: tuple[str, ...] = ()
    uncertainty_fields: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    regret_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class FakeE2E:
    request_id: str
    status: str
    explanation: FakeExplanation
    needs_user_input: bool = False
    highest_value_question: str | None = None
    human_final_decision: bool = True


@dataclass(frozen=True)
class FakeContextual:
    request_id: str
    status: str
    best_fit_candidate_id: str | None = None
    alternative_candidate_ids: tuple[str, ...] = ()
    uncertainty_fields: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    regret_risks: tuple[str, ...] = ()
    needs_user_input: bool = False
    highest_value_question: str | None = None
    human_final_decision: bool = True


class RealDecisionPresenterV1Test(unittest.TestCase):
    def test_01_e2e_preserves_best_candidate_and_uses_verified_name_from_result(self):
        r = FakeE2E(
            "r1", "recommended",
            FakeExplanation("p1", "บ้านเจ", ("p2",), (), (), ()),
        )
        p = present_end_to_end_decision_v1(r, candidate_labels={"p2": "ร้านสำรอง"})
        self.assertEqual(p.recommendation.candidate_id, "p1")
        self.assertEqual(p.recommendation.display_name, "บ้านเจ")
        self.assertEqual([x.candidate_id for x in p.alternatives], ["p2"])
        self.assertEqual(p.policy_version, PRESENTER_POLICY_VERSION)

    def test_02_contextual_preserves_best_and_alternative_order(self):
        r = FakeContextual("r2", "recommended", "p2", ("p3", "p1"))
        p = present_contextual_personal_decision_v1(
            r, candidate_labels={"p1": "หนึ่ง", "p2": "สอง", "p3": "สาม"}
        )
        self.assertEqual(p.recommendation.candidate_id, "p2")
        self.assertEqual([x.candidate_id for x in p.alternatives], ["p3", "p1"])

    def test_03_uncertainty_is_exposed_not_hidden(self):
        r = FakeContextual(
            "r3", "qualified_with_uncertainty", "p1",
            uncertainty_fields=("open_now", "price"),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.presentation_status, "recommendation_with_uncertainty")
        self.assertEqual(p.uncertainty_items, ("open_now", "price"))
        self.assertIn("ความไม่แน่นอน", p.summary)

    def test_04_tradeoff_and_regret_are_preserved_without_recalculation(self):
        r = FakeContextual(
            "r4", "recommended", "p1",
            tradeoffs=("farther_but_better_fit", "farther_but_better_fit"),
            regret_risks=("p1:regret=0.125",),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.tradeoff_items, ("farther_but_better_fit",))
        self.assertEqual(p.regret_items, ("p1:regret=0.125",))

    def test_05_needs_user_input_has_no_fake_recommendation(self):
        r = FakeContextual(
            "r5", "needs_user_input", None, needs_user_input=True,
            highest_value_question="ตอนนี้คุณอยู่บริเวณไหน?",
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.recommendation)
        self.assertEqual(p.presentation_status, "needs_user_input")
        self.assertEqual(p.highest_value_question, "ตอนนี้คุณอยู่บริเวณไหน?")

    def test_06_no_valid_candidate_remains_no_recommendation(self):
        r = FakeContextual("r6", "no_valid_candidate")
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.recommendation)
        self.assertEqual(p.presentation_status, "no_valid_candidate")

    def test_07_missing_label_falls_back_to_exact_candidate_id_not_guess(self):
        r = FakeContextual("r7", "recommended", "opaque-123")
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.recommendation.display_name, "opaque-123")

    def test_08_duplicate_alternative_and_best_are_not_repeated(self):
        r = FakeContextual("r8", "recommended", "p1", ("p1", "p2", "p2"))
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual([x.candidate_id for x in p.alternatives], ["p2"])

    def test_09_question_is_not_shown_when_engine_did_not_request_user_input(self):
        r = FakeContextual(
            "r9", "recommended", "p1",
            needs_user_input=False, highest_value_question="should not show",
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.highest_value_question)

    def test_10_human_final_decision_boundary_is_explicit(self):
        r = FakeContextual("r10", "recommended", "p1", human_final_decision=True)
        p = present_contextual_personal_decision_v1(r)
        self.assertTrue(p.human_final_decision)
        self.assertIn("ผู้ใช้เป็นผู้ตัดสินใจสุดท้าย", p.human_boundary)

    def test_11_presenter_does_not_promote_sponsor_or_reorder_anything(self):
        r = FakeContextual("r11", "recommended", "organic", ("sponsor", "other"))
        p = present_contextual_personal_decision_v1(
            r,
            candidate_labels={
                "organic": "Organic",
                "sponsor": "Sponsored",
                "other": "Other",
            },
        )
        self.assertEqual(p.recommendation.candidate_id, "organic")
        self.assertEqual([x.candidate_id for x in p.alternatives], ["sponsor", "other"])

    def test_12_insufficient_data_stays_fail_closed(self):
        r = FakeContextual(
            "r12", "insufficient_data", None,
            uncertainty_fields=("open_now",),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.recommendation)
        self.assertEqual(p.presentation_status, "insufficient_data")


if __name__ == "__main__":
    unittest.main()
