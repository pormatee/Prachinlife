from __future__ import annotations
import unittest
from place_platform_v2.production_quality import score_place, audit_production

class TestPhase31ProductionQuality(unittest.TestCase):
 def test_score_is_deterministic_and_evidence_only(self):
  p={'title':'A','location':{'latitude':1,'longitude':2,'province':'X'},'content_type':'service','source':'OSM','source_url':'https://x'}
  self.assertEqual(score_place(p),score_place(p)); self.assertEqual(score_place(p)['score'],70)
 def test_missing_contact_is_not_invented(self):
  q=score_place({'title':'A'}); self.assertFalse(q['actions']['phone']); self.assertFalse(q['actions']['website'])
 def test_primary_directory_filter(self):
  d={'vegetarian_index.json':[{'title':'hidden','metadata':{'show_in_primary_directory':False}},{'title':'shown','metadata':{'show_in_primary_directory':True}}]}
  self.assertEqual(audit_production(d)['visible_place_count'],1)
 def test_prachinlife_counts_eat_and_excludes_deals(self):
  d={'prachinlife_index.json':[{'content_type':'deal','title':'D'},{'content_type':'eat','title':'E'},{'content_type':'place','title':'legacy-shape'}]}
  r=audit_production(d)
  self.assertEqual(r['visible_place_count'],1)
  self.assertEqual(r['datasets']['prachinlife_index.json']['visible_places'],1)
 def test_audit_has_user_action_readiness(self):
  r=audit_production({'go_index.json':[{'title':'A','location':{'latitude':1,'longitude':2},'phone':'1'}]})
  self.assertEqual(r['action_ready']['map'],1); self.assertEqual(r['action_ready']['phone'],1)
 def test_enrichment_priorities_include_medium_places_missing_actions(self):
  rows=[
   {'id':'complete','title':'Complete','location':{'latitude':1,'longitude':2,'province':'X'},'content_type':'go','source':'OSM','source_url':'https://x','phone':'1','website':'https://w','prachinlife_page_url':'https://d'},
   {'id':'medium','title':'Medium','location':{'latitude':1,'longitude':2,'province':'X'},'content_type':'go','source':'OSM','source_url':'https://x'},
  ]
  r=audit_production({'go_index.json':rows})
  ids=[x['id'] for x in r['top_enrichment_priorities']]
  self.assertIn('medium',ids); self.assertNotIn('complete',ids)
  item=next(x for x in r['top_enrichment_priorities'] if x['id']=='medium')
  self.assertEqual(item['tier'],'medium')
  self.assertEqual(item['missing_actions'],['phone','website','additional_info'])
 def test_low_quality_priorities_are_ranked(self):
  r=audit_production({'go_index.json':[{'id':'b','title':'B'},{'id':'a'}]})
  self.assertEqual(r['top_enrichment_priorities'][0]['id'],'a')

if __name__=='__main__': unittest.main()
