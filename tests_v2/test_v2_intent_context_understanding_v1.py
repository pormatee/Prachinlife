from __future__ import annotations
import unittest

from place_platform_v2.intent_context_understanding_v1 import understand_user_request, build_consumer_decision_request


class IntentContextUnderstandingV1Test(unittest.TestCase):
    def test_pathum_tomorrow_vegetarian_request(self):
        r=understand_user_request("พรุ่งนี้จะไปปทุมธานี กินอาหารเจที่ไหนดี")
        self.assertEqual(r.goal,"find_place_to_eat")
        self.assertEqual(r.decision_type,"select")
        self.assertEqual(r.category,"vegetarian")
        self.assertEqual(r.province,"ปทุมธานี")
        self.assertEqual(r.temporal_context,"tomorrow")
        self.assertEqual([(c.key,c.value) for c in r.hard_constraints],[("province","ปทุมธานี"),("vegetarian",True)])
        self.assertIn("open_status_for_requested_time",r.unresolved_context)
        self.assertIn("exact_area_or_route",r.unresolved_context)

    def test_converts_to_consumer_request(self):
        r=understand_user_request("พรุ่งนี้จะไปปทุมธานี กินอาหารเจที่ไหนดี")
        c=r.to_consumer_request("req-1")
        self.assertEqual(c.category,"vegetarian")
        self.assertEqual(len(c.hard_constraints),2)
        self.assertEqual(c.hard_constraints[0].key,"province")
        self.assertEqual(c.hard_constraints[1].key,"vegetarian")

    def test_time_is_context_not_fabricated_open_constraint(self):
        r=understand_user_request("พรุ่งนี้จะไปปทุมธานี กินอาหารเจที่ไหนดี")
        self.assertNotIn("open_now",[c.key for c in r.hard_constraints])
        self.assertNotIn("open_tomorrow",[c.key for c in r.hard_constraints])
        self.assertIn("open_status_for_requested_time",r.unresolved_context)

    def test_near_me_requires_runtime_location_when_missing(self):
        r=understand_user_request("หาร้านเจใกล้ฉัน")
        self.assertTrue(r.near_me)
        self.assertEqual(r.category,"vegetarian")
        self.assertIn("current_location",r.unresolved_context)

    def test_near_me_accepts_trusted_current_location_context(self):
        r=understand_user_request("หาร้านเจใกล้ฉัน",{"current_location":(14.0,100.6)})
        self.assertNotIn("current_location",r.unresolved_context)
        self.assertEqual(r.inferred_context["current_location"],(14.0,100.6))

    def test_budget_context_is_preference_not_hard_constraint(self):
        r=understand_user_request("ปลายเดือนกินอะไรประหยัดที่ปราจีนบุรี")
        self.assertEqual(r.category,"eat")
        self.assertEqual(r.province,"ปราจีนบุรี")
        self.assertTrue(r.inferred_context["budget_sensitive"])
        self.assertEqual(r.preferences[0].key,"price")
        self.assertEqual(r.preferences[0].strength,"soft")
        self.assertIn("price",r.unresolved_context)

    def test_family_context_does_not_invent_place_facts(self):
        r=understand_user_request("พาครอบครัวไปกินข้าวที่ปราจีนบุรีไหนดี")
        self.assertEqual(r.category,"eat")
        self.assertTrue(r.inferred_context["family_context"])
        self.assertIn("family_suitability",r.unresolved_context)

    def test_unknown_category_fail_closed_before_consumer_request(self):
        r=understand_user_request("ช่วยหน่อย")
        self.assertIsNone(r.category)
        self.assertEqual(r.decision_type,"clarify")
        with self.assertRaises(ValueError):
            r.to_consumer_request("req-x")

    def test_bridge_builds_brain_contract(self):
        understood, req=build_consumer_decision_request("พรุ่งนี้จะไปปทุมธานี กินอาหารเจที่ไหนดี","req-bridge")
        self.assertEqual(understood.category,"vegetarian")
        self.assertEqual(req.request_id,"req-bridge")
        self.assertEqual(req.category,"vegetarian")
        self.assertEqual(tuple(c.key for c in req.hard_constraints),("province","vegetarian"))

    def test_no_provider_or_ranking_fields(self):
        r=understand_user_request("พรุ่งนี้จะไปปทุมธานี กินอาหารเจที่ไหนดี")
        self.assertFalse(hasattr(r,"best_fit_candidate_id"))
        self.assertFalse(hasattr(r,"provider"))

    def test_all_primary_categories(self):
        cases={
            "หาร้านอาหารที่ปราจีนบุรี":"eat",
            "หาร้านเจที่ปทุม":"vegetarian",
            "ซื้อของที่ปราจีนบุรีไหนดี":"shopping",
            "พรุ่งนี้เที่ยวปทุมไหนดี":"go",
            "หาร้านซ่อมที่ปราจีนบุรี":"service",
        }
        for text,category in cases.items():
            with self.subTest(text=text):
                self.assertEqual(understand_user_request(text).category,category)


if __name__ == "__main__":
    unittest.main()
