from __future__ import annotations
import unittest

from place_platform_v2.intent_context_understanding_v1 import understand_user_request, build_consumer_decision_request

class SemanticDecisionObjectV11Test(unittest.TestCase):
    def test_fuel_station_is_object_food_is_preference(self):
        r=understand_user_request("หาปั๊มไหนดีที่มีอาหารเยอะๆ")
        self.assertEqual(r.decision_object,"fuel_station")
        self.assertEqual(r.category,"service")
        self.assertEqual(r.goal,"find_fuel_station")
        self.assertIn(("food_variety","high"),[(p.key,p.value) for p in r.preferences])
        self.assertNotEqual(r.category,"eat")

    def test_restaurant_near_fuel_station_uses_fuel_station_as_reference(self):
        r=understand_user_request("หาร้านอาหารแถวปั๊ม ปตท. หน่อย")
        self.assertEqual(r.decision_object,"restaurant")
        self.assertEqual(r.category,"eat")
        self.assertIn("fuel_station",r.references)

    def test_same_words_reverse_semantic_roles(self):
        a=understand_user_request("หาปั๊มไหนดีที่มีร้านอาหารเยอะ")
        b=understand_user_request("หาร้านอาหารไหนดีแถวปั๊ม")
        self.assertEqual(a.decision_object,"fuel_station")
        self.assertEqual(b.decision_object,"restaurant")

    def test_parking_is_soft_when_optional(self):
        r=understand_user_request("หาร้านเจปทุม ถ้ามีที่จอดรถจะดี")
        self.assertEqual(r.decision_object,"restaurant")
        parking=[p for p in r.preferences if p.key=="parking"]
        self.assertEqual(len(parking),1)
        self.assertEqual(parking[0].strength,"soft")

    def test_parking_is_hard_when_user_says_must(self):
        r=understand_user_request("หาร้านเจปทุม ต้องมีที่จอดรถ")
        parking=[c for c in r.hard_constraints if c.key=="parking"]
        self.assertEqual(len(parking),1)
        self.assertEqual(parking[0].strength,"hard")

    def test_route_is_preference_not_goal(self):
        r=understand_user_request("หาร้านอาหารปทุมที่เป็นทางผ่านกลับกรุงเทพ")
        self.assertEqual(r.decision_object,"restaurant")
        self.assertEqual(r.goal,"find_place_to_eat")
        self.assertIn("route_fit",[p.key for p in r.preferences])

    def test_shopping_object_not_confused_by_food_word(self):
        r=understand_user_request("พรุ่งนี้ไปปทุม ซื้อของกินที่ไหนดี")
        self.assertEqual(r.decision_object,"shop")
        self.assertEqual(r.category,"shopping")

    def test_service_object_from_breakdown_request(self):
        r=understand_user_request("รถเสียปทุม หาร้านซ่อม")
        self.assertEqual(r.decision_object,"service_place")
        self.assertEqual(r.category,"service")

    def test_destination_object_with_family_context(self):
        r=understand_user_request("พาลูกเที่ยวปทุมไหนดี")
        self.assertEqual(r.decision_object,"destination")
        self.assertEqual(r.category,"go")
        self.assertTrue(r.inferred_context["family_context"])

    def test_vegetarian_object_keeps_dietary_hard_constraint(self):
        r=understand_user_request("พรุ่งนี้หาร้านเจปทุมไหนดี")
        self.assertEqual(r.decision_object,"restaurant")
        self.assertEqual(r.category,"vegetarian")
        self.assertIn(("vegetarian",True),[(c.key,c.value) for c in r.hard_constraints])

    def test_reference_does_not_enter_brain_as_category(self):
        understood,req=build_consumer_decision_request("หาร้านอาหารแถวปั๊ม ปตท.","semantic-1")
        self.assertEqual(understood.references,("fuel_station",))
        self.assertEqual(req.category,"eat")

    def test_time_context_still_does_not_fabricate_open_fact(self):
        r=understand_user_request("พรุ่งนี้หาปั๊มไหนดีที่มีอาหารเยอะ")
        self.assertIn("open_status_for_requested_time",r.unresolved_context)
        self.assertNotIn("open_tomorrow",[c.key for c in r.hard_constraints])
        self.assertNotIn("open_now",[c.key for c in r.hard_constraints])

    def test_unknown_sentence_still_fails_closed(self):
        r=understand_user_request("ช่วยเลือกให้หน่อย")
        self.assertIsNone(r.decision_object)
        self.assertIsNone(r.category)
        with self.assertRaises(ValueError):
            r.to_consumer_request("unknown")

    def test_decision_object_is_not_ranking_authority(self):
        r=understand_user_request("หาปั๊มไหนดี")
        self.assertFalse(hasattr(r,"best_fit_candidate_id"))
        self.assertFalse(hasattr(r,"ranking_score"))

    def test_complex_family_food_request_preserves_object_and_criteria(self):
        r=understand_user_request("พาครอบครัวไปปทุม อยากหาร้านอาหาร ราคาไม่แพง มีที่จอดรถ ถ้าเป็นทางผ่านจะดี")
        self.assertEqual(r.decision_object,"restaurant")
        self.assertEqual(r.category,"eat")
        keys=[p.key for p in r.preferences]
        self.assertIn("price",keys)
        self.assertIn("parking",keys)
        self.assertIn("route_fit",keys)
        self.assertTrue(r.inferred_context["family_context"])

if __name__ == "__main__":
    unittest.main()
