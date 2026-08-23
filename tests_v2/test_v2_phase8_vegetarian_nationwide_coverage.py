import json,tempfile,unittest
from pathlib import Path
from place_platform_v2.vegetarian_nationwide_coverage import *
class VegetarianNationwideCoverageTests(unittest.TestCase):
 def test_exactly_77_unique_provinces(self):self.assertEqual(77,len(PROVINCES));self.assertEqual(77,len(set(PROVINCES)))
 def test_plan_covers_every_province(self):
  p=build_plan();self.assertEqual(77*9,len(p));self.assertEqual(set(PROVINCES),{x['province'] for x in p})
 def test_eight_web_queries_each(self):
  p=build_plan();self.assertTrue(all(sum(x['channel']=='web_query' for x in p if x['province']==v)==8 for v in PROVINCES))
 def test_one_osm_sweep_each(self):
  p=build_plan();self.assertTrue(all(sum(x['channel']=='osm_province_sweep' for x in p if x['province']==v)==1 for v in PROVINCES))
 def test_stable_unique_job_ids(self):
  a=build_plan();b=build_plan();self.assertEqual([x['job_id'] for x in a],[x['job_id'] for x in b]);self.assertEqual(len(a),len({x['job_id'] for x in a}))
 def test_dedicated_is_primary_candidate(self):self.assertTrue(classify_candidate('ร้านอาหารเจ สุขใจ')['primary_candidate'])
 def test_diet_option_not_primary(self):self.assertFalse(classify_candidate('ร้านอาหารทั่วไป',{'diet:vegetarian':'yes'})['primary_candidate'])
 def test_unknown_fails_closed(self):self.assertEqual('UNRESOLVED',classify_candidate('ร้านอาหารทั่วไป',{})['scope'])
 def test_ledger_preserves_completed(self):
  p=build_plan();j=p[0];m=merge_plan_with_ledger(p,{'jobs':{j['job_id']:{'status':'completed','candidate_count':3}}});self.assertEqual('completed',m[0]['status']);self.assertEqual(3,m[0]['candidate_count'])
 def test_summary_never_claims_real_world_complete(self):self.assertFalse(coverage_summary(build_plan())['real_world_completeness_claimed'])
 def test_osm_query_has_diet_and_name_signals(self):
  q=build_osm_query(3600000000);self.assertIn('diet:vegetarian',q);self.assertIn('diet:vegan',q);self.assertIn('มังสวิรัติ',q);self.assertIn('เจ',q)
if __name__=='__main__':unittest.main()
