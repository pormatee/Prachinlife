import unittest
from pathlib import Path
from place_platform_v2.phase7_decision_assistant import DecisionCandidate,rank_candidates
ROOT=Path(__file__).resolve().parents[1]
class Phase7FinalTests(unittest.TestCase):
 def c(self,id,name,d=None,complete=0,life='active',cats=('restaurant',)):return DecisionCandidate(id,name,cats,life,d,complete)
 def test_near_complete_place_ranks_first(self):
  r=rank_candidates([self.c('a','A',1,4),self.c('b','B',15,1)]);self.assertEqual('a',r[0].candidate.place_id)
 def test_closed_place_excluded(self):self.assertEqual((),rank_candidates([self.c('a','A',1,5,'closed')]))
 def test_category_intent_boosts_matching_place(self):
  a=self.c('a','A',None,1,cats=('cafe',));b=self.c('b','B',None,1,cats=('restaurant',));self.assertEqual('a',rank_candidates([b,a],category='cafe')[0].candidate.place_id)
 def test_missing_distance_is_safe(self):self.assertEqual(1,len(rank_candidates([self.c('a','A',None,2)])))
 def test_negative_distance_rejected(self):self.assertEqual((),rank_candidates([self.c('a','A',-1,5)]))
 def test_deterministic_tie_break(self):self.assertEqual(['a','b'],[x.candidate.place_id for x in rank_candidates([self.c('b','Same'),self.c('a','Same')])])
 def test_frontend_engine_loaded_before_app(self):
  s=(ROOT/'index.html').read_text();self.assertLess(s.index('js/core/decision-assistant.js'),s.index('app.js?v='))
 def test_recommendation_uses_decision_engine(self):
  s=(ROOT/'app.js').read_text();self.assertIn('decisionAssistant',s);self.assertIn('getDecisionAssistantPlaces',s);self.assertIn('reasonText(entry.decision)',s)
 def test_no_unverified_fact_language(self):
  s=(ROOT/'js/core/decision-assistant.js').read_text();self.assertNotIn('ดีที่สุด',s);self.assertNotIn('เปิดอยู่',s)
if __name__=='__main__':unittest.main()
