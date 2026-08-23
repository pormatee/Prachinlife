import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.continued_discovery_batch import continue_discovery_batch
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text,canonical_name text,province text,phone text,website text,latitude real,longitude real)")
  c.execute("insert into places values('p1','อาหารเจ ซั่นสี่','ปราจีนบุรี','[\"0821389588\",\"0903853130\"]',null,14,101)")
  c.execute("create table precanonical_candidates(candidate_id text,candidate_key text,proposed_name text,province text,status text)")
  c.execute("insert into precanonical_candidates values('c1','k','ต้นหลิวอาหารเจ','ปราจีนบุรี','verified_identity')")
  c.execute("create table precanonical_pending_review(candidate_id text,status text,reason text,current_state text,next_action text)")
  c.execute("insert into precanonical_pending_review values('c1','pending_manual_confirmation','x','STILL_UNRESOLVED','confirm')")
  c.commit();c.close()
  prior={"new_place_candidates":[{"name":"มังสวิรัติ","province":"ปราจีนบุรี"}]};pp=r/"prior.json";pp.write_text(json.dumps(prior),encoding="utf-8")
  return td,r,db,pp
 def runobs(self,r,db,pp,obs):
  p=r/"o.json";p.write_text(json.dumps(obs),encoding="utf-8")
  return continue_discovery_batch(database_path=db,observations_path=p,prior_discovery_report_path=pp)
 def test_existing_phone_alias_is_not_new(self):
  td,r,db,pp=self.fixture();self.addCleanup(td.cleanup)
  x=self.runobs(r,db,pp,[{"name":"อาหารเจ ปราจีนบุรี","province":"ปราจีนบุรี","phone":"0903853130","source_name":"w"}])
  self.assertEqual(x["batch_results"][0]["batch_state"],"EXISTING_CANONICAL")
 def test_pending_candidate_is_skipped_not_blocking(self):
  td,r,db,pp=self.fixture();self.addCleanup(td.cleanup)
  x=self.runobs(r,db,pp,[{"name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_name":"x"}])
  self.assertEqual(x["batch_results"][0]["batch_state"],"PENDING_MANUAL_REVIEW");self.assertTrue(x["discovery_continues"])
 def test_prior_discovery_is_not_rediscovered(self):
  td,r,db,pp=self.fixture();self.addCleanup(td.cleanup)
  x=self.runobs(r,db,pp,[{"name":"มังสวิรัติ","province":"ปราจีนบุรี","source_name":"x"}])
  self.assertEqual(x["batch_results"][0]["batch_state"],"KNOWN_DISCOVERY_CANDIDATE")
 def test_two_sources_group_into_one_new_candidate(self):
  td,r,db,pp=self.fixture();self.addCleanup(td.cleanup)
  obs=[{"candidate_group":"amita","name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"a"},
       {"candidate_group":"amita","name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"b"}]
  x=self.runobs(r,db,pp,obs);self.assertEqual(x["new_candidate_count"],1)
  self.assertEqual(x["verification_queue"][0]["independent_source_family_count"],2)
  self.assertTrue(x["verification_queue"][0]["identity_evidence_ready"])
 def test_one_source_new_candidate_requests_second_source(self):
  td,r,db,pp=self.fixture();self.addCleanup(td.cleanup)
  x=self.runobs(r,db,pp,[{"name":"ฉันทนา","province":"ปราจีนบุรี","source_family":"news"}])
  self.assertTrue(x["verification_queue"][0]["needs_second_independent_source"])
 def test_zero_write(self):
  td,r,db,pp=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes()
  x=self.runobs(r,db,pp,[]);self.assertEqual(b,db.read_bytes());self.assertTrue(x["safety"]["database_unchanged"])
if __name__=="__main__":unittest.main()
