from __future__ import annotations
import unittest
from place_platform_v2.consumer_decision_contract_v1 import *
class T(unittest.TestCase):
 def req(self,**k): return ConsumerDecisionRequest('r1',k.get('goal','test'),k.get('category','eat'),k.get('hard_constraints',()),k.get('preferences',()),k.get('context',ConsumerContext()))
 def test_categories(self):
  for c in ('eat','vegetarian','shopping','go','service'): self.assertEqual(self.req(category=c).category,c)
 def test_hard_satisfied(self):
  r=self.req(hard_constraints=(ConsumerCondition('open_now',True,'hard'),)); c=CandidateDecisionView('c',{'open_now':True},(MaterialEvidence('open_now','verified',True),)); a=resolve_hard_constraints(r,c); self.assertEqual(a[0].resolution,ConstraintResolution.SATISFIED); self.assertTrue(hard_constraint_eligible(r,c)[0])
 def test_hard_violation(self):
  r=self.req(hard_constraints=(ConsumerCondition('open_now',True,'hard'),)); c=CandidateDecisionView('c',{'open_now':False},(MaterialEvidence('open_now','verified',False),)); a=resolve_hard_constraints(r,c); self.assertEqual(a[0].resolution,ConstraintResolution.VIOLATED); self.assertFalse(hard_constraint_eligible(r,c)[0])
 def test_missing_is_unresolved_not_satisfied_or_false(self):
  r=self.req(hard_constraints=(ConsumerCondition('open_now',True,'hard'),)); c=CandidateDecisionView('c',{}); a=resolve_hard_constraints(r,c); self.assertEqual(a[0].resolution,ConstraintResolution.UNRESOLVED); self.assertFalse(hard_constraint_eligible(r,c)[0]); self.assertEqual(hard_constraint_eligible(r,c)[1],())
 def test_stale_matching_value_is_still_unresolved(self):
  r=self.req(hard_constraints=(ConsumerCondition('open_now',True,'hard'),)); c=CandidateDecisionView('c',{'open_now':True},(MaterialEvidence('open_now','stale',True),)); self.assertEqual(resolve_hard_constraints(r,c)[0].resolution,ConstraintResolution.UNRESOLVED)
 def test_operators(self):
  c=CandidateDecisionView('c',{'distance_km':2.0,'tags':['jay','cafe'],'name':'Baan J'},(MaterialEvidence('distance_km','verified',2.0),MaterialEvidence('tags','verified',['jay','cafe']),MaterialEvidence('name','verified','Baan J')))
  for cond in (ConsumerCondition('distance_km',3,'hard',operator='lte'),ConsumerCondition('tags','jay','hard',operator='contains'),ConsumerCondition('name',None,'hard',operator='required')): self.assertEqual(resolve_hard_constraint(cond,c).resolution,ConstraintResolution.SATISFIED)
 def test_uncertainty(self):
  c=CandidateDecisionView('c',{},(MaterialEvidence('vegetarian','verified',True),MaterialEvidence('open_now','missing'))); self.assertEqual(material_uncertainty(c,('vegetarian','open_now')),('open_now',))
 def test_promo(self): self.assertTrue(promotion_can_affect_value(relevant=True,valid=True,eligible=True,linked=True)); self.assertFalse(promotion_can_affect_value(relevant=True,valid=False,eligible=True,linked=True))
 def test_sponsor(self): self.assertFalse(sponsorship_affects_organic_fit(CandidateDecisionView('c',{},is_sponsored=True)))
 def test_question_and_effort(self):
  self.assertEqual(decision_effort_questions(decision_can_materially_change=False,enough_for_useful_answer=True),0); self.assertEqual(decision_effort_questions(decision_can_materially_change=True,enough_for_useful_answer=False),1)
 def test_outcome_question(self):
  with self.assertRaises(ValueError): ConsumerDecisionOutcome('r',None,(),(),True,None,())
 def test_human(self):
  with self.assertRaises(ValueError): ConsumerDecisionOutcome('r','c',(),(),False,None,(),False)
if __name__=='__main__': unittest.main()
