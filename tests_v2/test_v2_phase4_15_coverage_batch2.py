import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.coverage_batch2 import continue_coverage_batch2
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text,canonical_name text,province text,phone text)")
  c.execute("create table precanonical_candidates(candidate_id text,candidate_key text,proposed_name text,province text,status text)")
  c.execute("create table precanonical_pending_review(candidate_id text,status text,reason text,current_state text,next_action text)")
  c.execute("insert into precanonical_candidates values('c1','k','AMITA VEGAN','ปราจีนบุรี','x')")
  c.execute("insert into precanonical_pending_review values('c1','pending_coordinate_confirmation','geo','UNRESOLVED','confirm')")
  c.commit();c.close()
  bp=r/"b.json";bp.write_text(json.dumps({"batch_results":[{"name":"ฉันทนา","province":"ปราจีนบุรี"}]}),encoding="utf-8")
  ip=r/"i.json";ip.write_text(json.dumps({"decisions":[]}),encoding="utf-8")
  return td,r,db,bp,ip
 def execute(self,r,db,bp,ip,obs):
  p=r/"o.json";p.write_text(json.dumps(obs),encoding="utf-8")
  return continue_coverage_batch2(database_path=db,observations_path=p,prior_batch_path=bp,prior_identity_report_path=ip)
 def test_category_only_listing_is_not_primary_ready(self):
  td,r,db,bp,ip=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,bp,ip,[{"name":"น้ำเต้าหู้","province":"ปราจีนบุรี","source_family":"w","source_category":"อาหารเจ","discovery_signal":"category_only"}])
  self.assertEqual(x["results"][0]["batch_state"],"NEW_CATEGORY_CANDIDATE");self.assertFalse(x["results"][0]["primary_directory_ready"])
 def test_named_jay_candidate_is_dedicated_signal(self):
  td,r,db,bp,ip=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,bp,ip,[{"name":"ร้านอาหารเจใหม่","province":"ปราจีนบุรี","source_family":"w","source_category":"อาหารเจ"}])
  self.assertEqual(x["results"][0]["batch_state"],"NEW_DEDICATED_CANDIDATE")
 def test_pending_is_skipped(self):
  td,r,db,bp,ip=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,bp,ip,[{"name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"w"}])
  self.assertEqual(x["results"][0]["batch_state"],"PENDING_REVIEW");self.assertTrue(x["discovery_continues"])
 def test_known_candidate_is_not_rediscovered(self):
  td,r,db,bp,ip=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,bp,ip,[{"name":"ฉันทนา","province":"ปราจีนบุรี","source_family":"news","discovery_signal":"named_jay_report"}])
  self.assertEqual(x["results"][0]["batch_state"],"KNOWN_CANDIDATE")
 def test_zero_write(self):
  td,r,db,bp,ip=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes()
  x=self.execute(r,db,bp,ip,[]);self.assertEqual(b,db.read_bytes());self.assertTrue(x["safety"]["database_unchanged"])
if __name__=="__main__":unittest.main()
