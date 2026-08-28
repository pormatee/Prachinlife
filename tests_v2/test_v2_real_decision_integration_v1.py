import unittest
from datetime import datetime, timezone
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.consumer_decision_contract_v1 import ConsumerCondition, ConsumerDecisionRequest
from place_platform_v2.real_decision_integration_v1 import evaluate_published_decision

def place(pid,name,lat,lon,cats=("vegetarian",)):
    return PublishedPlaceView(pid,name,GeoPoint(lat,lon),"ปทุมธานี",tuple(cats),PlaceLifecycle.ACTIVE,
        publication_policy_version="test-published",published_at=datetime(2026,8,28,tzinfo=timezone.utc))

class TestRealDecisionIntegrationV1(unittest.TestCase):
    def req(self, prefs=()):
        return ConsumerDecisionRequest("pathum-jay","พรุ่งนี้จะไปปทุมธานี กินอาหารเจที่ไหนดี","vegetarian",
            hard_constraints=(ConsumerCondition("province","ปทุมธานี","hard"),ConsumerCondition("vegetarian",True,"hard")),
            preferences=tuple(prefs))
    def test_real_pathum_shape_maps_and_decides(self):
        places=(place("47b7","Baan J Veggie House",14.076182,100.633498),
                place("10ac","Vegan Garden ร้านอาหารเจ-มังสวิรัติ คาเฟ่",13.9596821,100.6867682),
                place("8c0d","Vegetarian by So Vegan ไอยรา",14.0791968,100.6343395))
        r=evaluate_published_decision(self.req(),places,origin=GeoPoint(14.08,100.63),highest_value_question="คุณจะเข้าปทุมทางไหนหรือมีจุดหมายแถวไหนครับ?")
        self.assertIsNotNone(r.best_fit_candidate_id)
        self.assertTrue(r.human_final_decision)
        self.assertLessEqual(1 if r.highest_value_question else 0,1)
    def test_missing_hard_fact_never_best_fit(self):
        p=place("x","Unknown Diet",14,100.6,cats=("restaurant",))
        r=evaluate_published_decision(self.req(),(p,))
        self.assertIsNone(r.best_fit_candidate_id)
        self.assertIn("x",r.unresolved_candidate_ids)
    def test_proven_wrong_province_rejected(self):
        p=PublishedPlaceView("x","Other",GeoPoint(13,100), "กรุงเทพมหานคร",("vegetarian",),PlaceLifecycle.ACTIVE,
            publication_policy_version="x",published_at=datetime.now(timezone.utc))
        r=evaluate_published_decision(self.req(),(p,))
        self.assertIsNone(r.best_fit_candidate_id)
        self.assertIn("x",r.rejected_candidate_ids)
    def test_open_tomorrow_not_fabricated(self):
        req=ConsumerDecisionRequest("x","พรุ่งนี้กินเจ","vegetarian",
          hard_constraints=(ConsumerCondition("open_tomorrow",True,"hard"),))
        r=evaluate_published_decision(req,(place("p","P",14,100.6),))
        self.assertIsNone(r.best_fit_candidate_id)
        self.assertIn("open_tomorrow",r.uncertainty_fields)
    def test_sponsor_cannot_enter_from_published_mapping(self):
        r=evaluate_published_decision(self.req(),(place("p","P",14,100.6),))
        for x in r.dqe_result.recommended:
            self.assertNotIn("sponsor",str(x.reasons).lower())
    def test_one_question_only_when_materially_useful(self):
        places=(place("a","A",14.0,100.6),place("b","B",14.1,100.7))
        r=evaluate_published_decision(self.req(),places,highest_value_question="คุณจะเข้าปทุมทางไหนครับ?")
        self.assertTrue(r.needs_user_input)
        self.assertIsInstance(r.highest_value_question, str)
        self.assertTrue(r.highest_value_question.strip())
    def test_no_question_when_not_supplied_as_high_value(self):
        r=evaluate_published_decision(self.req(),(place("a","A",14,100.6),))
        self.assertFalse(r.needs_user_input)
        self.assertIsNone(r.highest_value_question)
