from __future__ import annotations

from dataclasses import dataclass
import unittest

from place_platform_v2.real_decision_presenter_v1 import (
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


class RealDecisionPresenterV1Challenge(unittest.TestCase):
    def test_01_sponsor_label_cannot_replace_best_candidate(self):
        r = FakeContextual("c1", "recommended", "organic", ("sponsor",))
        p = present_contextual_personal_decision_v1(
            r,
            candidate_labels={
                "organic": "ร้านธรรมดา",
                "sponsor": "⭐ ร้านแนะนำพิเศษ ⭐",
            },
        )
        self.assertEqual(p.recommendation.candidate_id, "organic")

    def test_02_alternative_label_cannot_be_promoted_to_headline(self):
        r = FakeContextual("c2", "recommended", "best", ("alt",))
        p = present_contextual_personal_decision_v1(
            r, candidate_labels={"best": "Best", "alt": "อันดับหนึ่ง"}
        )
        self.assertIn("Best", p.summary)
        self.assertNotIn("อันดับหนึ่ง", p.summary)

    def test_03_untrusted_label_markup_is_display_only_not_decision_authority(self):
        r = FakeContextual("c3", "recommended", "p1", ("p2",))
        p = present_contextual_personal_decision_v1(
            r, candidate_labels={"p1": "<script>best</script>", "p2": "p2"}
        )
        self.assertEqual(p.recommendation.candidate_id, "p1")
        self.assertEqual(p.recommendation.display_name, "<script>best</script>")

    def test_04_no_recommendation_is_not_invented_from_alternatives(self):
        r = FakeContextual("c4", "no_valid_candidate", None, ("p1", "p2"))
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.recommendation)
        self.assertEqual(p.presentation_status, "no_valid_candidate")

    def test_05_needs_user_input_cannot_be_overridden_by_labels(self):
        r = FakeContextual(
            "c5", "needs_user_input", None, ("p1",),
            needs_user_input=True,
            highest_value_question="คุณอยู่ที่ไหนตอนนี้?",
        )
        p = present_contextual_personal_decision_v1(
            r, candidate_labels={"p1": "ร้านที่ควรเลือกทันที"}
        )
        self.assertIsNone(p.recommendation)
        self.assertEqual(p.highest_value_question, "คุณอยู่ที่ไหนตอนนี้?")

    def test_06_uncertainty_order_is_preserved_after_dedupe(self):
        r = FakeContextual(
            "c6", "recommended", "p1",
            uncertainty_fields=("open_now", "price", "open_now", "parking"),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.uncertainty_items, ("open_now", "price", "parking"))

    def test_07_tradeoff_order_is_preserved_after_dedupe(self):
        r = FakeContextual(
            "c7", "recommended", "p1",
            tradeoffs=("farther", "cheaper", "farther", "less_evidence"),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.tradeoff_items, ("farther", "cheaper", "less_evidence"))

    def test_08_regret_order_is_preserved_after_dedupe(self):
        r = FakeContextual(
            "c8", "recommended", "p1",
            regret_risks=("distance", "uncertain_hours", "distance"),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.regret_items, ("distance", "uncertain_hours"))

    def test_09_empty_and_whitespace_items_are_removed_only(self):
        r = FakeContextual(
            "c9", "recommended", "p1",
            uncertainty_fields=("", " ", "open_now"),
            tradeoffs=(" ", "farther"),
            regret_risks=("", "risk"),
        )
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.uncertainty_items, ("open_now",))
        self.assertEqual(p.tradeoff_items, ("farther",))
        self.assertEqual(p.regret_items, ("risk",))

    def test_10_missing_best_label_never_borrows_alternative_name(self):
        r = FakeContextual("c10", "recommended", "opaque-best", ("alt",))
        p = present_contextual_personal_decision_v1(
            r, candidate_labels={"alt": "ชื่อร้านจริงของ alt"}
        )
        self.assertEqual(p.recommendation.display_name, "opaque-best")

    def test_11_e2e_verified_best_name_cannot_change_best_id(self):
        r = FakeE2E(
            "c11", "recommended",
            FakeExplanation("p1", "ชื่อจาก explanation", ("p2",)),
        )
        p = present_end_to_end_decision_v1(
            r, candidate_labels={"p1": "ชื่อ caller", "p2": "ชื่อ p2"}
        )
        self.assertEqual(p.recommendation.candidate_id, "p1")

    def test_12_e2e_caller_label_has_precedence_over_embedded_name_only_for_display(self):
        r = FakeE2E(
            "c12", "recommended",
            FakeExplanation("p1", "ชื่อ embedded", ()),
        )
        p = present_end_to_end_decision_v1(
            r, candidate_labels={"p1": "ชื่อ display ที่ caller ยืนยัน"}
        )
        self.assertEqual(p.recommendation.candidate_id, "p1")
        self.assertEqual(p.recommendation.display_name, "ชื่อ display ที่ caller ยืนยัน")

    def test_13_human_boundary_present_even_with_clean_recommendation(self):
        r = FakeContextual("c13", "recommended", "p1")
        p = present_contextual_personal_decision_v1(r)
        self.assertTrue(p.human_final_decision)
        self.assertIn("ผู้ใช้เป็นผู้ตัดสินใจสุดท้าย", p.human_boundary)

    def test_14_human_boundary_present_for_fail_closed_result(self):
        r = FakeContextual("c14", "no_valid_candidate", None)
        p = present_contextual_personal_decision_v1(r)
        self.assertTrue(p.human_final_decision)
        self.assertIn("ผู้ใช้เป็นผู้ตัดสินใจสุดท้าย", p.human_boundary)

    def test_15_presenter_does_not_create_question_when_engine_has_none(self):
        r = FakeContextual("c15", "needs_user_input", None, needs_user_input=True)
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.highest_value_question)

    def test_16_status_text_does_not_cause_re_ranking(self):
        r = FakeContextual("c16", "sponsor_featured_best_deal", "organic", ("sponsor",))
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual(p.recommendation.candidate_id, "organic")

    def test_17_unknown_status_with_no_best_stays_no_recommendation(self):
        r = FakeContextual("c17", "weird_future_status", None)
        p = present_contextual_personal_decision_v1(r)
        self.assertIsNone(p.recommendation)
        self.assertEqual(p.presentation_status, "no_recommendation")

    def test_18_duplicate_alternatives_never_change_first_seen_order(self):
        r = FakeContextual("c18", "recommended", "p0", ("p2", "p1", "p2", "p3", "p1"))
        p = present_contextual_personal_decision_v1(r)
        self.assertEqual([x.candidate_id for x in p.alternatives], ["p2", "p1", "p3"])


if __name__ == "__main__":
    unittest.main()
