import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.precanonical_evidence_persistence import persist_verified_precanonical_evidence
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();root=Path(td.name);db=root/"x.sqlite3"
  c=sqlite3.connect(db)
  c.execute("create table places(place_id text primary key,canonical_name text)")
  c.execute("create table place_evidence(evidence_id text primary key)")
  c.execute("create table other_table(k text)");c.execute("insert into places values('p1','Existing')");c.commit();c.close()
  vr={"decisions":[{"candidate_key":"abc","name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","identity_outcome":"VERIFIED_IDENTITY",
                    "independent_source_family_count":2,"source_families":["a","b"],"lifecycle_conflicts":["open_vs_closed_source_conflict"],
                    "canonical_duplicate_matches":[]}]}
  ev=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"a","source_name":"A","source_url":"https://a","evidence_kind":"identity"},
      {"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"b","source_name":"B","source_url":"https://b","evidence_kind":"identity"}]
  vp=root/"v.json";ep=root/"e.json";vp.write_text(json.dumps(vr),encoding="utf-8");ep.write_text(json.dumps(ev),encoding="utf-8")
  return td,db,vp,ep
 def execute(self,db,vp,ep,commit=False):
  return persist_verified_precanonical_evidence(database_path=db,verification_report_path=vp,evidence_observations_path=ep,commit=commit)
 def test_dry_run_is_zero_write(self):
  td,db,vp,ep=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes();r=self.execute(db,vp,ep)
  self.assertEqual(r["prepared_candidate_count"],1);self.assertEqual(r["prepared_evidence_count"],2);self.assertEqual(b,db.read_bytes())
 def test_commit_writes_only_precanonical_tables(self):
  td,db,vp,ep=self.fixture();self.addCleanup(td.cleanup);r=self.execute(db,vp,ep,True)
  self.assertEqual(r["inserted_candidate_count"],1);self.assertEqual(r["inserted_evidence_count"],2)
  self.assertTrue(r["safety"]["canonical_rows_unchanged"]);self.assertTrue(r["safety"]["place_evidence_unchanged"])
 def test_lifecycle_conflict_is_preserved_not_resolved(self):
  td,db,vp,ep=self.fixture();self.addCleanup(td.cleanup);self.execute(db,vp,ep,True)
  c=sqlite3.connect(db);raw=c.execute("select lifecycle_conflict_json from precanonical_candidates").fetchone()[0];c.close()
  self.assertIn("open_vs_closed_source_conflict",raw)
 def test_idempotent_replay(self):
  td,db,vp,ep=self.fixture();self.addCleanup(td.cleanup);self.execute(db,vp,ep,True);r=self.execute(db,vp,ep,True)
  self.assertEqual(r["inserted_candidate_count"],0);self.assertEqual(r["inserted_evidence_count"],0)
  self.assertEqual(r["already_present_candidate_count"],1);self.assertEqual(r["already_present_evidence_count"],2)
 def test_supported_identity_is_not_persisted(self):
  td,db,vp,ep=self.fixture();self.addCleanup(td.cleanup)
  x=json.loads(vp.read_text());x["decisions"][0]["identity_outcome"]="SUPPORTED_IDENTITY";vp.write_text(json.dumps(x))
  r=self.execute(db,vp,ep,True);self.assertEqual(r["prepared_candidate_count"],0)
 def test_independent_source_guard(self):
  td,db,vp,ep=self.fixture();self.addCleanup(td.cleanup)
  x=json.loads(ep.read_text());x[1]["source_family"]="a";ep.write_text(json.dumps(x))
  r=self.execute(db,vp,ep,True);self.assertEqual(r["prepared_candidate_count"],0)
  self.assertEqual(r["blocked_counts"]["independent_source_guard"],1)
if __name__=="__main__":unittest.main()
