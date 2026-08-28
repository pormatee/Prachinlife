import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.read_model import InMemoryPublishedPlaceRepository
from place_platform_v2.contextual_personal_decision_v1 import DecisionTimeFact, run_contextual_personal_decision_v1


def place(pid,name,cats=("restaurant",),lat=14.08,lon=100.63):
    return PublishedPlaceView(pid,name,GeoPoint(lat,lon),"ปทุมธานี",cats,PlaceLifecycle.ACTIVE,publication_policy_version="ctx-test",published_at=datetime.now(timezone.utc))


def fact(pid,field,value,state="verified",conf=1.0):
    return DecisionTimeFact(pid,field,value,state,f"decision-time:test:{pid}:{field}","2026-08-28T12:00:00+07:00",conf)

class T(unittest.TestCase):
    def repo(self,*places):
        r=InMemoryPublishedPlaceRepository()
        for p in places:r.upsert_published(p)
        return r

    def test_now_requires_verified_open_now(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="1",user_text="หาร้านอาหารปทุมตอนนี้",repository=r,decision_time_facts=[fact("a","open_now",True),fact("b","open_now",False)])
        self.assertEqual(out.best_fit_candidate_id,"a")
        self.assertIn("b",out.rejected_candidate_ids)
        self.assertIn("urgent_now_requires_open_now",out.profile.applied_rules)

    def test_now_missing_open_fact_is_unresolved_not_best(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="2",user_text="หาร้านอาหารปทุมตอนนี้",repository=r)
        self.assertIsNone(out.best_fit_candidate_id)
        self.assertIn("a",out.unresolved_candidate_ids)
        self.assertIn("open_now",out.uncertainty_fields)

    def test_family_context_prefers_supported_family_fit(self):
        r=self.repo(place("a","A"),place("b","B"))
        facts=[fact("a","family_suitability",True),fact("a","parking",True),fact("b","family_suitability",False),fact("b","parking",False)]
        out=run_contextual_personal_decision_v1(request_id="3",user_text="หาร้านอาหารปทุมไปกับลูก",repository=r,decision_time_facts=facts)
        self.assertEqual(out.best_fit_candidate_id,"a")
        self.assertIn("family_prefers_suitability_and_parking",out.profile.applied_rules)

    def test_budget_context_prefers_lower_normalized_price(self):
        r=self.repo(place("a","A"),place("b","B"))
        facts=[fact("a","price",0.2),fact("b","price",0.8)]
        out=run_contextual_personal_decision_v1(request_id="4",user_text="หาร้านอาหารปทุมปลายเดือน",repository=r,decision_time_facts=facts)
        self.assertEqual(out.best_fit_candidate_id,"a")
        self.assertIn("budget_prefers_lower_price",out.profile.applied_rules)

    def test_explicit_budget_cap_is_hard(self):
        r=self.repo(place("a","A"),place("b","B"))
        facts=[fact("a","price_amount",90),fact("b","price_amount",150)]
        out=run_contextual_personal_decision_v1(request_id="5",user_text="หาร้านอาหารปทุม",repository=r,context={"budget_max":100},decision_time_facts=facts)
        self.assertEqual(out.best_fit_candidate_id,"a")
        self.assertIn("b",out.rejected_candidate_ids)

    def test_novelty_uses_trusted_visit_history_only(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="6",user_text="หาร้านอาหารปทุม อยากลองร้านใหม่",repository=r,visited_candidate_ids=["a"])
        self.assertEqual(out.best_fit_candidate_id,"b")
        self.assertIn("prefer_unvisited_option",out.profile.applied_rules)
        self.assertIn("user-context:visited-history",out.applied_fact_refs)

    def test_no_visit_history_means_novelty_unknown(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="7",user_text="หาร้านอาหารปทุม อยากลองร้านใหม่",repository=r)
        self.assertIn("novelty",out.uncertainty_fields)

    def test_stale_dynamic_fact_does_not_become_truth(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="8",user_text="หาร้านอาหารปทุมตอนนี้",repository=r,decision_time_facts=[fact("a","open_now",True,"stale",0.5)])
        self.assertIsNone(out.best_fit_candidate_id)
        self.assertIn("a",out.unresolved_candidate_ids)

    def test_near_me_without_location_still_no_ranking(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="9",user_text="หาร้านอาหารใกล้ฉัน",repository=r)
        self.assertIsNone(out.best_fit_candidate_id)
        self.assertTrue(out.needs_user_input)

    def test_human_final_decision_preserved(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="10",user_text="หาร้านอาหารปทุม",repository=r)
        self.assertTrue(out.human_final_decision)

if __name__=='__main__': unittest.main()
