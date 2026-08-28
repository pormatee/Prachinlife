from __future__ import annotations

import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.end_to_end_real_decision_flow_v1 import run_end_to_end_real_decision_flow_v1
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.read_model import InMemoryPublishedPlaceRepository
from place_platform_v2.real_candidate_mapping_v1 import published_place_to_decision_candidate


def place(pid, name, lat, lon, categories, province="ปทุมธานี"):
    return PublishedPlaceView(
        place_id=pid,
        name=name,
        location=GeoPoint(lat, lon),
        province=province,
        categories=tuple(categories),
        lifecycle=PlaceLifecycle.ACTIVE,
        publication_policy_version="test-published-v1",
        published_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
    )


class TestEndToEndRealDecisionFlowV1(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryPublishedPlaceRepository()
        for p in (
            place("baanj", "Baan J Veggie House", 14.076182, 100.633498, ("vegetarian", "restaurant")),
            place("vegan-garden", "Vegan Garden", 14.0800, 100.6400, ("vegan", "restaurant")),
            place("fuel-a", "Fuel A", 14.0770, 100.6340, ("fuel_station", "service")),
            place("shop-a", "Shop A", 14.0900, 100.6500, ("shopping",)),
        ):
            self.repo.upsert_published(p)

    def test_01_semantic_object_limits_candidate_type(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r1",
            user_text="หาปั๊มไหนดีที่มีอาหารเยอะๆ ปทุมธานี",
            repository=self.repo,
        )
        self.assertEqual(r.understanding.decision_object, "fuel_station")
        self.assertEqual(r.compatible_candidate_ids, ("fuel-a",))
        self.assertNotIn("baanj", r.compatible_candidate_ids)

    def test_02_reverse_semantic_role_restaurant_near_fuel_reference(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r2",
            user_text="หาร้านอาหารแถวปั๊ม ปทุมธานี",
            repository=self.repo,
        )
        self.assertEqual(r.understanding.decision_object, "restaurant")
        self.assertIn("fuel_station", r.understanding.references)
        self.assertIn("baanj", r.compatible_candidate_ids)
        self.assertNotIn("fuel-a", r.compatible_candidate_ids)

    def test_03_missing_hard_fact_cannot_be_best_fit(self):
        # Generic restaurant category does not prove vegetarian=True.
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(place("generic", "Generic Restaurant", 14.08, 100.64, ("restaurant",)))
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r3",
            user_text="หาร้านเจปทุมธานี",
            repository=repo,
        )
        self.assertIsNotNone(r.decision)
        self.assertIsNone(r.decision.best_fit_candidate_id)
        self.assertEqual(r.decision.unresolved_candidate_ids, ("generic",))
        self.assertIn("vegetarian", r.decision.uncertainty_fields)
        self.assertEqual(r.status, "insufficient_data")

    def test_04_missing_nonhard_fact_is_uncertainty_not_fact(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r4",
            user_text="หาร้านเจราคาประหยัด ปทุมธานี",
            repository=self.repo,
        )
        self.assertIsNotNone(r.decision.best_fit_candidate_id)
        self.assertIn("price", r.decision.uncertainty_fields)
        self.assertTrue(any("price" in x for x in r.decision.tradeoffs))

    def test_05_near_me_without_location_asks_one_question_and_does_not_rank(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r5",
            user_text="หาร้านเจใกล้ฉัน",
            repository=self.repo,
        )
        self.assertEqual(r.status, "needs_user_input")
        self.assertTrue(r.needs_user_input)
        self.assertIsNotNone(r.highest_value_question)
        self.assertIsNone(r.decision)

    def test_06_near_me_uses_trusted_location(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r6",
            user_text="หาร้านเจใกล้ฉัน",
            repository=self.repo,
            context={"current_location": (14.0762, 100.6335)},
            radius_km=2.0,
        )
        self.assertFalse(r.needs_user_input)
        self.assertIn("baanj", r.compatible_candidate_ids)
        self.assertIsNotNone(r.decision.best_fit_candidate_id)

    def test_07_typo_normalization_survives_end_to_end(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r7",
            user_text="หารัานเจ ปทุมทานี",
            repository=self.repo,
        )
        self.assertEqual(r.understanding.province, "ปทุมธานี")
        self.assertEqual(r.understanding.category, "vegetarian")
        self.assertIn("baanj", r.compatible_candidate_ids)

    def test_08_mapper_cannot_import_sponsor_or_promotion_into_organic_candidate(self):
        p = place("fuel", "Fuel", 14.07, 100.63, ("fuel_station", "service"))
        c = published_place_to_decision_candidate(p)
        self.assertFalse(c.is_sponsored)
        self.assertIsNone(c.promotion_ref)

    def test_09_explanation_exposes_tradeoff_uncertainty_regret_and_human_boundary(self):
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r9",
            user_text="หาร้านเจราคาประหยัด ปทุมธานี",
            repository=self.repo,
        )
        self.assertTrue(r.explanation.human_final_decision)
        self.assertTrue(r.human_final_decision)
        self.assertTrue(r.explanation.why_fit)
        self.assertIn("price", r.explanation.uncertainty_fields)
        self.assertTrue(r.explanation.regret_risks)

    def test_10_only_published_read_model_is_required(self):
        class ReadOnlySpy(InMemoryPublishedPlaceRepository):
            def upsert_published(self, place):
                return super().upsert_published(place)
            def remove_published(self, place_id):
                raise AssertionError("E2E must not call mutation API")
        repo = ReadOnlySpy()
        repo.upsert_published(place("baanj", "Baan J", 14.076, 100.633, ("vegetarian", "restaurant")))
        r = run_end_to_end_real_decision_flow_v1(
            request_id="r10", user_text="หาร้านเจปทุมธานี", repository=repo
        )
        self.assertIn("baanj", r.compatible_candidate_ids)


if __name__ == "__main__":
    unittest.main()
