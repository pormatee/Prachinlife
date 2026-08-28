import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.read_model import InMemoryPublishedPlaceRepository
from place_platform_v2.contextual_personal_decision_v1 import DecisionTimeFact, run_contextual_personal_decision_v1


def place(pid,name,province="ปทุมธานี",cats=("restaurant",),lat=14.08,lon=100.63):
    return PublishedPlaceView(pid,name,GeoPoint(lat,lon),province,cats,PlaceLifecycle.ACTIVE,publication_policy_version="ctx-challenge",published_at=datetime.now(timezone.utc))

def fact(pid,field,value,state="verified",conf=1.0,obs="2026-08-28T12:00:00+07:00",ref=None):
    return DecisionTimeFact(pid,field,value,state,ref or f"decision-time:challenge:{pid}:{field}",obs,conf)

class T(unittest.TestCase):
    def repo(self,*places):
        r=InMemoryPublishedPlaceRepository()
        for p in places:r.upsert_published(p)
        return r

    def test_01_now_true_beats_false(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="1",user_text="หาร้านอาหารปทุมตอนนี้",repository=r,decision_time_facts=[fact("a","open_now",True),fact("b","open_now",False)])
        self.assertEqual(out.best_fit_candidate_id,"a"); self.assertIn("b",out.rejected_candidate_ids)

    def test_02_now_conflicting_is_unresolved(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="2",user_text="หาร้านอาหารปทุมตอนนี้",repository=r,decision_time_facts=[fact("a","open_now",True,"conflicting")])
        self.assertIsNone(out.best_fit_candidate_id); self.assertIn("a",out.unresolved_candidate_ids)

    def test_03_now_unknown_is_unresolved(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="3",user_text="หาร้านอาหารปทุมตอนนี้",repository=r,decision_time_facts=[fact("a","open_now",None,"unknown",0.0)])
        self.assertIsNone(out.best_fit_candidate_id); self.assertIn("open_now",out.uncertainty_fields)

    def test_04_family_soft_does_not_reject_missing(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="4",user_text="หาร้านอาหารปทุมไปกับลูก",repository=r,decision_time_facts=[fact("a","family_suitability",True),fact("a","parking",True)])
        self.assertNotIn("b",out.rejected_candidate_ids); self.assertIn("family_suitability",out.uncertainty_fields)

    def test_05_budget_soft_does_not_become_hard(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="5",user_text="หาร้านอาหารปทุมปลายเดือน",repository=r,decision_time_facts=[fact("a","price",0.8),fact("b","price",0.2)])
        self.assertEqual(out.best_fit_candidate_id,"b"); self.assertEqual(out.rejected_candidate_ids,())

    def test_06_budget_cap_missing_price_is_unresolved(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="6",user_text="หาร้านอาหารปทุม",repository=r,context={"budget_max":100},decision_time_facts=[fact("a","price_amount",90)])
        self.assertEqual(out.best_fit_candidate_id,"a"); self.assertIn("b",out.unresolved_candidate_ids)

    def test_07_budget_cap_over_limit_rejected(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="7",user_text="หาร้านอาหารปทุม",repository=r,context={"budget_max":100},decision_time_facts=[fact("a","price_amount",150)])
        self.assertIsNone(out.best_fit_candidate_id); self.assertIn("a",out.rejected_candidate_ids)

    def test_08_novelty_without_history_never_invents(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="8",user_text="หาร้านอาหารปทุม อยากลองร้านใหม่",repository=r)
        self.assertIn("novelty",out.uncertainty_fields); self.assertNotIn("user-context:visited-history",out.applied_fact_refs)

    def test_09_novelty_with_history_is_deterministic(self):
        r=self.repo(place("a","A"),place("b","B"))
        out=run_contextual_personal_decision_v1(request_id="9",user_text="หาร้านอาหารปทุม อยากลองร้านใหม่",repository=r,visited_candidate_ids=["a"])
        self.assertEqual(out.best_fit_candidate_id,"b")

    def test_10_wrong_province_not_considered(self):
        r=self.repo(place("a","A","ปทุมธานี"),place("b","B","ปราจีนบุรี"))
        out=run_contextual_personal_decision_v1(request_id="10",user_text="หาร้านอาหารปทุม",repository=r,decision_time_facts=[fact("a","price",0.8),fact("b","price",0.1)])
        self.assertNotEqual(out.best_fit_candidate_id,"b"); self.assertNotIn("b",out.alternative_candidate_ids)

    def test_11_near_me_without_location_no_ranking_even_with_facts(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="11",user_text="หาร้านอาหารใกล้ฉันตอนนี้",repository=r,decision_time_facts=[fact("a","open_now",True)])
        self.assertIsNone(out.best_fit_candidate_id); self.assertTrue(out.needs_user_input)

    def test_12_unrelated_fact_cannot_satisfy_hard_open(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="12",user_text="หาร้านอาหารปทุมตอนนี้",repository=r,decision_time_facts=[fact("a","parking",True)])
        self.assertIsNone(out.best_fit_candidate_id); self.assertIn("open_now",out.uncertainty_fields)

    def test_13_duplicate_fact_refs_do_not_duplicate_output(self):
        r=self.repo(place("a","A"))
        f=fact("a","price",0.2,ref="source:x")
        out=run_contextual_personal_decision_v1(request_id="13",user_text="หาร้านอาหารปทุมปลายเดือน",repository=r,decision_time_facts=[f,f])
        self.assertEqual(out.applied_fact_refs.count("source:x"),1)

    def test_14_human_final_decision_always_preserved(self):
        r=self.repo(place("a","A"))
        out=run_contextual_personal_decision_v1(request_id="14",user_text="หาร้านอาหารปทุม",repository=r)
        self.assertTrue(out.human_final_decision)

if __name__=='__main__': unittest.main()
