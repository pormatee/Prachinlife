import unittest
from place_platform_v2.vegetarian_web_pilot import *
class WebPilotTests(unittest.TestCase):
 def test_primary_name(self):self.assertTrue(classify_web_observation({'name':'ร้านอาหารเจ A'})['primary_candidate'])
 def test_option_not_primary(self):
  r=classify_web_observation({'name':'ร้านทั่วไป','evidence_text':'มีเมนูเจ','option_available':True});self.assertEqual('OPTION_AVAILABLE',r['directory_scope']);self.assertFalse(r['primary_candidate'])
 def test_guess_rejected(self):self.assertEqual('UNRESOLVED',classify_web_observation({'name':'ร้านทั่วไป','description':'น่าจะมีอาหารเจ'})['directory_scope'])
 def test_source_family(self):self.assertEqual('wongnai.com',source_family('https://www.wongnai.com/x'))
 def test_requires_province(self):self.assertIsNone(normalize_web_observation({'name':'ร้านเจ','province':'เชียงใหม่','source_url':'https://x.test/a'}))
 def test_dedup_name(self):
  a={'name':'ร้านอาหารเจ A','province':'ชลบุรี','source_url':'https://a.test/1'};b={'name':'ร้านอาหารเจ A','province':'ชลบุรี','source_url':'https://b.test/2'};self.assertEqual(1,len(dedupe_web_observations([a,b])))
 def test_zero_gate_fails(self):self.assertEqual('FAIL',build_pilot_report([],[])['status'])
 def test_each_province_required(self):
  rows=[{'name':'ร้านอาหารเจ A','province':p,'source_url':f'https://x.test/{i}'} for i,p in enumerate(PILOT_PROVINCES)];self.assertEqual('PASS',build_pilot_report(rows,[])['status'])
 def test_no_writes(self):
  rows=[{'name':'ร้านอาหารเจ A','province':p,'source_url':f'https://x.test/{i}'} for i,p in enumerate(PILOT_PROVINCES)];r=build_pilot_report(rows,[]);self.assertFalse(r['automatic_adoption']);self.assertFalse(r['production_writes'])
if __name__=='__main__':unittest.main()
