import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.lifecycle_conflict_resolution import resolve_lifecycle_conflict
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();root=Path(td.name);db=root/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("""create table precanonical_candidates(candidate_id text primary key,proposed_name text,province text)""")
  c.execute("""create table precanonical_evidence(evidence_id text,candidate_id text,phone text)""")
  c.execute("insert into precanonical_candidates values('c1','ต้นหลิวอาหารเจ','ปราจีนบุรี')")
  c.execute("insert into precanonical_evidence values('e1','c1','095-917-6495')");c.commit();c.close()
  return td,root,db
 def runobs(self,root,db,obs):
  p=root/"o.json";p.write_text(json.dumps(obs),encoding="utf-8")
  return resolve_lifecycle_conflict(database_path=db,fresh_observations_path=p)
 def test_one_fresh_closed_source_is_not_enough(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup)
  x=self.runobs(r,db,[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","phone":"0959176495","source_family":"a","lifecycle_status":"permanently_closed"}])
  self.assertEqual(x["decisions"][0]["resolution_outcome"],"UNRESOLVED_NEEDS_DIRECT_CONFIRMATION")
 def test_two_independent_matching_closed_sources_resolve(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup)
  obs=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","phone":"0959176495","source_family":f,"lifecycle_status":"permanently_closed"} for f in ("a","b")]
  x=self.runobs(r,db,obs);self.assertEqual(x["decisions"][0]["resolution_outcome"],"RESOLVED");self.assertEqual(x["decisions"][0]["resolved_lifecycle"],"permanently_closed")
 def test_different_phone_branch_is_excluded(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup)
  o={"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจสาขา2ปิดขายถาวร","province":"ปราจีนบุรี","phone":"0879658287","source_family":"x","lifecycle_status":"permanently_closed","identity_scope":"possible_other_branch"}
  x=self.runobs(r,db,[o]);self.assertEqual(len(x["decisions"][0]["excluded_observations"]),1)
 def test_conflicting_fresh_sources_remain_unresolved(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup)
  obs=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","phone":"0959176495","source_family":"a","lifecycle_status":"open"},
       {"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","phone":"0959176495","source_family":"b","lifecycle_status":"permanently_closed"}]
  x=self.runobs(r,db,obs);self.assertEqual(x["decisions"][0]["resolution_outcome"],"UNRESOLVED_CONFLICTING_FRESH_EVIDENCE")
 def test_zero_write(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes();x=self.runobs(r,db,[])
  self.assertEqual(b,db.read_bytes());self.assertTrue(x["safety"]["database_unchanged"])
if __name__=="__main__":unittest.main()
