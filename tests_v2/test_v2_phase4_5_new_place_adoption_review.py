import sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.new_place_adoption_review import review_new_place_adoption

class T(unittest.TestCase):
 def fixture(self, conflict=True):
  td=tempfile.TemporaryDirectory();db=Path(td.name)/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text primary key,canonical_name text,province text,phone text)")
  c.execute("""create table precanonical_candidates(candidate_id text primary key,candidate_key text,
   proposed_name text,province text,category text,identity_outcome text,independent_source_family_count integer,
   lifecycle_conflict_json text,status text,policy_version text,created_at text)""")
  c.execute("""create table precanonical_evidence(evidence_id text primary key,candidate_id text,source_type text,
   source_name text,source_family text,source_record_id text,source_url text,observed_name text,province text,
   phone text,website text,lifecycle_status text,evidence_kind text,payload_json text,policy_version text,created_at text)""")
  cf='["open_vs_closed_source_conflict"]' if conflict else '[]'
  c.execute("insert into precanonical_candidates values(?,?,?,?,?,?,?,?,?,?,?)",
   ("c1","k1","ต้นหลิวอาหารเจ","ปราจีนบุรี","vegetarian","VERIFIED_IDENTITY",2,cf,"verified_identity","p","t"))
  life=["open","permanently_closed"] if conflict else ["open","open"]
  for i,f in enumerate(["a","b"]):
   c.execute("insert into precanonical_evidence values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    (f"e{i}","c1","web",f.upper(),f,None,f"https://{f}","ต้นหลิวอาหารเจ","ปราจีนบุรี",
     "095-917-6495",None,life[i],"identity","{}","p","t"))
  c.commit();c.close();return td,db
 def test_current_conflict_needs_review(self):
  td,db=self.fixture();self.addCleanup(td.cleanup);r=review_new_place_adoption(database_path=db)
  self.assertEqual(r["decision_counts"],{"NEEDS_REVIEW":1})
  self.assertEqual(r["decisions"][0]["proposed_lifecycle"],None)
 def test_resolved_evidence_can_be_ready(self):
  td,db=self.fixture(False);self.addCleanup(td.cleanup);r=review_new_place_adoption(database_path=db)
  self.assertEqual(r["decision_counts"],{"READY":1})
 def test_duplicate_name_same_province_blocks(self):
  td,db=self.fixture(False);self.addCleanup(td.cleanup);c=sqlite3.connect(db)
  c.execute("insert into places values('p1','ต้นหลิวอาหารเจ','ปราจีนบุรี',null)");c.commit();c.close()
  r=review_new_place_adoption(database_path=db);self.assertEqual(r["decision_counts"],{"BLOCKED":1})
 def test_duplicate_phone_blocks_even_other_province(self):
  td,db=self.fixture(False);self.addCleanup(td.cleanup);c=sqlite3.connect(db)
  c.execute("insert into places values('p1','Other','เชียงใหม่','0959176495')");c.commit();c.close()
  r=review_new_place_adoption(database_path=db);self.assertEqual(r["decision_counts"],{"BLOCKED":1})
 def test_generic_name_other_province_does_not_block(self):
  td,db=self.fixture(False);self.addCleanup(td.cleanup);c=sqlite3.connect(db)
  c.execute("insert into places values('p1','ต้นหลิวอาหารเจ','เชียงใหม่',null)");c.commit();c.close()
  r=review_new_place_adoption(database_path=db);self.assertEqual(r["decision_counts"],{"READY":1})
 def test_review_is_zero_write(self):
  td,db=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes()
  r=review_new_place_adoption(database_path=db);self.assertEqual(b,db.read_bytes())
  self.assertTrue(r["safety"]["database_unchanged"]);self.assertFalse(r["safety"]["automatic_lifecycle_resolution"])
if __name__=="__main__":unittest.main()
