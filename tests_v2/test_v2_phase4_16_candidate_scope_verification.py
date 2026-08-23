import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.candidate_scope_verification import verify_candidate_scope
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/'x.sqlite3';c=sqlite3.connect(db);c.execute('create table x(a)');c.commit();c.close();return td,r,db
 def runx(self,queue,obs):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);q=r/'q.json';o=r/'o.json';q.write_text(json.dumps({'followup_queue':queue}),encoding='utf-8');o.write_text(json.dumps(obs),encoding='utf-8');return verify_candidate_scope(database_path=db,coverage_report_path=q,scope_observations_path=o)
 def test_category_label_alone_does_not_verify(self):
  q=[{'candidate_key':'1','name':'น้ำเต้าหู้','province':'ปราจีนบุรี','candidate_scope':'category_only'}];x=self.runx(q,[{'candidate_key':'1','source_family':'wongnai','observed_categories':'อาหารเจ'}]);self.assertEqual(x['decisions'][0]['scope_outcome'],'SCOPE_UNRESOLVED')
 def test_general_business_is_excluded_from_primary(self):
  q=[{'candidate_key':'1','name':'ร้านทั่วไป','province':'ปราจีนบุรี','candidate_scope':'category_only'}];x=self.runx(q,[{'candidate_key':'1','source_family':'wongnai','scope_signal':'general_food_business','merchant_description':'น้ำเต้าหู้ นมสด'}]);self.assertEqual(x['decisions'][0]['scope_outcome'],'GENERAL_OR_MIXED_SCOPE');self.assertFalse(x['decisions'][0]['primary_directory_ready'])
 def test_dedicated_scope_needs_independent_source_for_verified(self):
  q=[{'candidate_key':'1','name':'ร้าน','province':'ปราจีนบุรี','candidate_scope':'category_only'}];x=self.runx(q,[{'candidate_key':'1','source_family':'wongnai','scope_signal':'dedicated_diet_business'}]);self.assertEqual(x['decisions'][0]['scope_outcome'],'DEDICATED_SCOPE_SUPPORTED')
 def test_dedicated_scope_with_independent_source_verifies(self):
  q=[{'candidate_key':'1','name':'ร้าน','province':'ปราจีนบุรี','candidate_scope':'category_only'}];x=self.runx(q,[{'candidate_key':'1','source_family':'local-news','scope_signal':'dedicated_diet_business'}]);self.assertEqual(x['decisions'][0]['scope_outcome'],'DEDICATED_SCOPE_VERIFIED');self.assertTrue(x['decisions'][0]['primary_directory_ready'])
 def test_zero_write(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes();q=r/'q';o=r/'o';q.write_text('{"followup_queue":[]}');o.write_text('[]');x=verify_candidate_scope(database_path=db,coverage_report_path=q,scope_observations_path=o);self.assertEqual(b,db.read_bytes());self.assertTrue(x['safety']['database_unchanged'])
if __name__=='__main__':unittest.main()
