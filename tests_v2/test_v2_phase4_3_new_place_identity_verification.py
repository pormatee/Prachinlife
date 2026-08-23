import sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.new_place_identity_verification import verify_new_place_candidates
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();p=Path(td.name)/"x.sqlite3";c=sqlite3.connect(p)
  c.execute("create table places(place_id text,canonical_name text,province text,phone text,website text,latitude real,longitude real)")
  c.execute("insert into places values(?,?,?,?,?,?,?)",("p1","Existing","ปราจีนบุรี",None,None,14,101));c.commit();c.close()
  d={"new_place_candidates":[{"name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","phone":"095-917-6495"}]}
  return td,p,d
 def test_two_source_families_verify_identity(self):
  td,p,d=self.fixture();self.addCleanup(td.cleanup)
  e=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_name":"A","source_family":"a","source_url":"https://a.test","phone":"0959176495"},
     {"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_name":"B","source_family":"b","source_url":"https://b.test","phone":"0959176495"}]
  r=verify_new_place_candidates(p,d,e);self.assertEqual(r["decisions"][0]["identity_outcome"],"VERIFIED_IDENTITY")
  self.assertEqual(r["decisions"][0]["phone_independent_source_family_count"],2)
 def test_same_family_does_not_fake_independence(self):
  td,p,d=self.fixture();self.addCleanup(td.cleanup)
  e=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"same","source_url":"https://x/a"},
     {"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"same","source_url":"https://x/b"}]
  r=verify_new_place_candidates(p,d,e);self.assertEqual(r["decisions"][0]["identity_outcome"],"SUPPORTED_IDENTITY")
 def test_existing_canonical_blocks_creation(self):
  td,p,d=self.fixture();self.addCleanup(td.cleanup);d["new_place_candidates"][0]["name"]="Existing"
  e=[{"candidate_name":"Existing","observed_name":"Existing","province":"ปราจีนบุรี","source_family":"a","source_url":"https://a"}]
  r=verify_new_place_candidates(p,d,e);self.assertEqual(r["decisions"][0]["identity_outcome"],"BLOCKED_EXISTING_CANONICAL")
 def test_same_generic_name_in_other_province_does_not_block(self):
  td,p,d=self.fixture();self.addCleanup(td.cleanup)
  c=sqlite3.connect(p);c.execute("insert into places values(?,?,?,?,?,?,?)",("p2","ต้นหลิวอาหารเจ","เชียงใหม่",None,None,18,99));c.commit();c.close()
  e=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"a","source_url":"https://a"}]
  r=verify_new_place_candidates(p,d,e);self.assertEqual(r["decisions"][0]["identity_outcome"],"SUPPORTED_IDENTITY")
 def test_lifecycle_conflict_does_not_destroy_identity_verification(self):
  td,p,d=self.fixture();self.addCleanup(td.cleanup)
  e=[{"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"a","source_url":"https://a","lifecycle_status":"open"},
     {"candidate_name":"ต้นหลิวอาหารเจ","observed_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","source_family":"b","source_url":"https://b","lifecycle_status":"permanently_closed"}]
  r=verify_new_place_candidates(p,d,e);x=r["decisions"][0]
  self.assertEqual(x["identity_outcome"],"VERIFIED_IDENTITY");self.assertTrue(x["lifecycle_conflicts"])
 def test_read_only_safety(self):
  td,p,d=self.fixture();self.addCleanup(td.cleanup);b=p.read_bytes()
  r=verify_new_place_candidates(p,d,[]);self.assertEqual(b,p.read_bytes());self.assertTrue(r["safety"]["database_unchanged"])
if __name__=="__main__":unittest.main()
