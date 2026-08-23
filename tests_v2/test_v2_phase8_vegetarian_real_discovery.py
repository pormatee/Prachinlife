import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from place_platform_v2.vegetarian_real_discovery import *
class RealDiscoveryTests(unittest.TestCase):
 def test_query_is_province_scoped(self):
  q=build_province_osm_query('ปราจีนบุรี');self.assertIn('ปราจีนบุรี',q);self.assertIn('diet:vegetarian',q);self.assertIn('diet:vegan',q)
 def test_named_shop_is_primary(self):
  x=normalize_osm_element({'type':'node','id':1,'lat':1,'lon':2,'tags':{'name':'ร้านอาหารเจ สุขใจ'}},'ตราด');self.assertTrue(x['primary_candidate'])
 def test_option_is_not_primary(self):
  x=normalize_osm_element({'type':'node','id':2,'lat':1,'lon':2,'tags':{'name':'Cafe A','diet:vegetarian':'yes'}},'ตราด');self.assertEqual('OPTION_AVAILABLE',x['directory_scope']);self.assertFalse(x['primary_candidate'])
 def test_unknown_is_rejected(self):
  self.assertIsNone(normalize_osm_element({'type':'node','id':3,'lat':1,'lon':2,'tags':{'name':'Cafe B'}},'ตราด'))
 def test_web_export_is_616_jobs(self):self.assertEqual(77*8,len(build_web_job_export()))
 def test_dedupe_osm_id(self):
  a={'observation_id':'x','name':'A'};b={'observation_id':'x','name':'B'};self.assertEqual('B',dedupe_observations([a,b])[0]['name'])
 def test_resumable_completed_is_skipped(self):
  with tempfile.TemporaryDirectory() as d:
   lp=Path(d)/'l.json';op=Path(d)/'o.json'; calls=[]
   def f(q):calls.append(q);return SimpleNamespace(elements=(),endpoint='test',attempts=1)
   a=run_osm_discovery(ledger_path=lp,observations_path=op,provinces=['ตราด'],fetcher=f,sleep_seconds=0)
   b=run_osm_discovery(ledger_path=lp,observations_path=op,provinces=['ตราด'],fetcher=f,sleep_seconds=0)
   self.assertEqual(1,len(calls));self.assertEqual(1,a['completed_this_run']);self.assertEqual(0,b['attempted_this_run'])
 def test_failure_is_persisted(self):
  with tempfile.TemporaryDirectory() as d:
   lp=Path(d)/'l.json';op=Path(d)/'o.json'
   def f(q):raise RuntimeError('network')
   r=run_osm_discovery(ledger_path=lp,observations_path=op,provinces=['ตราด'],fetcher=f,sleep_seconds=0)
   self.assertEqual(1,r['failed_this_run']);self.assertEqual('failed',json.loads(lp.read_text())['provinces']['ตราด']['status'])
 def test_no_completeness_claim(self):
  with tempfile.TemporaryDirectory() as d:
   r=run_osm_discovery(ledger_path=Path(d)/'l',observations_path=Path(d)/'o',provinces=[],fetcher=lambda q:None,sleep_seconds=0)
   self.assertFalse(r['real_world_completeness_claimed'])
 def test_no_auto_adoption_or_prod_write(self):
  with tempfile.TemporaryDirectory() as d:
   r=run_osm_discovery(ledger_path=Path(d)/'l',observations_path=Path(d)/'o',provinces=[],fetcher=lambda q:None,sleep_seconds=0)
   self.assertFalse(r['automatic_adoption']);self.assertFalse(r['production_writes'])
if __name__=='__main__':unittest.main()
