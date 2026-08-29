from __future__ import annotations
import unittest
from place_platform_v2.master_super_brain_v1 import DecisionCandidate, DecisionConstraint, DecisionPreference, DecisionRequest, EvidenceItem
from place_platform_v2.decision_quality_engine_v1 import evaluate_decision_quality

def ev(f,v,s="verified",c=1.0,r=None): return EvidenceItem(f,v,s,c,source_ref=r)

class DecisionQualityChallengeV1Tests(unittest.TestCase):
    def test_near_stale_vs_far_reliable(self):
        q=DecisionRequest("c1","veg dinner",category="vegetarian",constraints=(DecisionConstraint("vegetarian","eq",True,"hard",10),DecisionConstraint("open_now","eq",True,"soft",5)),preferences=(DecisionPreference("distance_norm","prefer_low",2),))
        a=DecisionCandidate("near","place",{"vegetarian":True,"open_now":True,"distance_norm":.05},(ev("vegetarian",True),ev("open_now",True,"stale",.45),ev("distance_norm",.05)))
        b=DecisionCandidate("safe","place",{"vegetarian":True,"open_now":True,"distance_norm":.45},(ev("vegetarian",True),ev("open_now",True,"verified",.98),ev("distance_norm",.45)))
        r=evaluate_decision_quality(q,(a,b)); self.assertEqual(r.lower_regret_candidate_id,"safe"); self.assertEqual(r.recommended[0].candidate_id,"safe")

    def test_cheap_unknown_stock_vs_verified(self):
        q=DecisionRequest("c2","buy today",category="shopping",constraints=(DecisionConstraint("in_stock","eq",True,"soft",8),),preferences=(DecisionPreference("price_norm","prefer_low",3),))
        a=DecisionCandidate("cheap","branch",{"in_stock":True,"price_norm":.02,"distance_norm":.1},(ev("in_stock",True,"unknown",0),ev("price_norm",.02),ev("distance_norm",.1)))
        b=DecisionCandidate("safe","branch",{"in_stock":True,"price_norm":.45,"distance_norm":.25},(ev("in_stock",True,"verified",.98),ev("price_norm",.45),ev("distance_norm",.25)))
        r=evaluate_decision_quality(q,(a,b)); self.assertEqual(r.lower_regret_candidate_id,"safe"); self.assertEqual(r.recommended[0].candidate_id,"safe")

    def test_upside_vs_lower_regret(self):
        q=DecisionRequest("c3","outing",category="go",preferences=(DecisionPreference("excitement","prefer_high",5),))
        a=DecisionCandidate("upside","activity",{"excitement":1.0,"open_now":True,"weather_fit":1.0,"travel_time_norm":.2},(ev("excitement",1),ev("open_now",True,"stale",.5),ev("weather_fit",1,"stale",.5),ev("travel_time_norm",.2)))
        b=DecisionCandidate("safe","activity",{"excitement":.65,"open_now":True,"weather_fit":1.0,"travel_time_norm":.25},(ev("excitement",.65),ev("open_now",True),ev("weather_fit",1),ev("travel_time_norm",.25)))
        r=evaluate_decision_quality(q,(a,b)); self.assertEqual(r.upside_candidate_id,"upside"); self.assertEqual(r.lower_regret_candidate_id,"safe")

    def test_conflicting_evidence_exposed(self):
        q=DecisionRequest("c4","service now",category="service",constraints=(DecisionConstraint("capability_match","eq",True,"hard",10),))
        a=DecisionCandidate("svc","service",{"capability_match":True,"available_now":True,"distance_norm":.2},(ev("capability_match",True),ev("available_now",True,"conflicting",.8,"A"),ev("distance_norm",.2)))
        r=evaluate_decision_quality(q,(a,)); self.assertIn("available_now:conflicting",r.recommended[0].uncertainties)

    def test_all_hard_fail(self):
        q=DecisionRequest("c5","veg",category="vegetarian",constraints=(DecisionConstraint("vegetarian","eq",True,"hard",10),))
        cs=(DecisionCandidate("a","place",{"vegetarian":False},(ev("vegetarian",False),)),DecisionCandidate("b","place",{"vegetarian":False},(ev("vegetarian",False),)))
        r=evaluate_decision_quality(q,cs); self.assertEqual(r.status,"no_valid_candidate"); self.assertFalse(r.recommended)

    def test_missing_material_evidence_fail_closed(self):
        q=DecisionRequest("c6","eat",category="eat")
        a=DecisionCandidate("x","place",{"open_now":True,"distance_norm":.2,"diet_match":1},())
        r=evaluate_decision_quality(q,(a,)); self.assertEqual(r.status,"insufficient_data"); self.assertTrue(r.clarifying_question)

    def test_hard_constraint_beats_extreme_preference(self):
        q=DecisionRequest("c7","service",category="service",constraints=(DecisionConstraint("capability_match","eq",True,"hard",100),),preferences=(DecisionPreference("distance_norm","prefer_low",1000),))
        a=DecisionCandidate("wrong","service",{"capability_match":False,"available_now":True,"distance_norm":0},(ev("capability_match",False),ev("available_now",True),ev("distance_norm",0)))
        b=DecisionCandidate("right","service",{"capability_match":True,"available_now":True,"distance_norm":.9},(ev("capability_match",True),ev("available_now",True),ev("distance_norm",.9)))
        r=evaluate_decision_quality(q,(a,b)); self.assertEqual([x.candidate_id for x in r.recommended],["right"])

    def test_sponsor_cannot_rescue_weaker_candidate(self):
        q=DecisionRequest("c8","shop",category="shopping",preferences=(DecisionPreference("price_norm","prefer_low",2),))
        a=DecisionCandidate("good","branch",{"in_stock":True,"price_norm":.2,"distance_norm":.2},(ev("in_stock",True),ev("price_norm",.2),ev("distance_norm",.2)),False)
        b=DecisionCandidate("sponsor","branch",{"in_stock":True,"price_norm":.8,"distance_norm":.6},(ev("in_stock",True),ev("price_norm",.8),ev("distance_norm",.6)),True)
        self.assertEqual(evaluate_decision_quality(q,(a,b)).recommended[0].candidate_id,"good")

    def test_provider_parity(self):
        kw=dict(request_id="c9",goal="dinner",category="eat",preferences=(DecisionPreference("distance_norm","prefer_low",2),))
        cs=(DecisionCandidate("a","place",{"open_now":True,"distance_norm":.2,"diet_match":1},(ev("open_now",True),ev("distance_norm",.2),ev("diet_match",1))),DecisionCandidate("b","place",{"open_now":True,"distance_norm":.4,"diet_match":1},(ev("open_now",True),ev("distance_norm",.4),ev("diet_match",1))))
        a=evaluate_decision_quality(DecisionRequest(**kw,provider="openai"),cs); b=evaluate_decision_quality(DecisionRequest(**kw,provider="deepseek"),cs)
        self.assertEqual([(x.candidate_id,x.organic_score,x.regret_risk) for x in a.recommended],[(x.candidate_id,x.organic_score,x.regret_risk) for x in b.recommended])

    def test_deterministic_tie(self):
        q=DecisionRequest("c10","compare",category="shopping"); attrs={"in_stock":True,"price_norm":.3,"distance_norm":.3}; e=(ev("in_stock",True),ev("price_norm",.3),ev("distance_norm",.3))
        z=DecisionCandidate("z","branch",attrs,e); a=DecisionCandidate("a","branch",attrs,e)
        self.assertEqual([x.candidate_id for x in evaluate_decision_quality(q,(z,a)).recommended],["z", "a"])
        self.assertEqual([x.candidate_id for x in evaluate_decision_quality(q,(a,z)).recommended],["a","z"])

    def test_fact_inference_preference_separation(self):
        q=DecisionRequest("c11","food",category="eat",preferences=(DecisionPreference("distance_norm","prefer_low",1),))
        a=DecisionCandidate("x","place",{"open_now":True,"distance_norm":.2,"diet_match":1},(ev("open_now",True),ev("distance_norm",.2),ev("diet_match",1)))
        kinds={x.kind for x in evaluate_decision_quality(q,(a,)).recommended[0].reasons}
        self.assertTrue({"fact","inference","user_preference"}.issubset(kinds))

    def test_human_boundary_preserved(self):
        q=DecisionRequest("c12","eat",category="eat")
        a=DecisionCandidate("x","place",{"open_now":True,"distance_norm":.2,"diet_match":1},(ev("open_now",True),ev("distance_norm",.2),ev("diet_match",1)))
        self.assertTrue(evaluate_decision_quality(q,(a,)).decision_boundary.human_decides)

if __name__=="__main__": unittest.main()
