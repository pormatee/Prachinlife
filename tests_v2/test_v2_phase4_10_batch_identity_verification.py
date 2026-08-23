import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.batch_identity_verification import verify_batch_identities
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text,canonical_name text,province text,phone text)")
  c.commit();c.close()
  batch={"verification_queue":[
   {"candidate_key":"a","name":"AMITA VEGAN","province":"ปราจีนบุรี","category":"vegetarian"},
   {"candidate_key":"b","name":"ฉันทนา","province":"ปราจีนบุรี","category":"vegetarian"}]}
  bp=r/"b.json";bp.write_text(json.dumps(batch),encoding="utf-8")
  return td,r,db,bp
 def execute(self,r,db,bp,ev):
  ep=r/"e.json";ep.write_text(json.dumps(ev),encoding="utf-8")
  return verify_batch_identities(database_path=db,batch_report_path=bp,evidence_path=ep)
 def test_two_independent_sources_verify_one_candidate(self):
  td,r,db,bp=self.fixture();self.addCleanup(td.cleanup)
  ev=[{"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"a"},
      {"candidate_name":"AMITA VEGAN","observed_name":"ร้านอาหารเจ AMITA VEGAN","province":"ปราจีนบุรี","source_family":"b"}]
  x=self.execute(r,db,bp,ev);self.assertEqual(x["decisions"][0]["identity_outcome"],"VERIFIED_IDENTITY")
 def test_one_source_remains_supported(self):
  td,r,db,bp=self.fixture();self.addCleanup(td.cleanup)
  ev=[{"candidate_name":"ฉันทนา","observed_name":"ฉันทนา","province":"ปราจีนบุรี","source_family":"news"}]
  x=self.execute(r,db,bp,ev);d=[z for z in x["decisions"] if z["name"]=="ฉันทนา"][0]
  self.assertEqual(d["identity_outcome"],"SUPPORTED_IDENTITY")
 def test_same_family_does_not_count_twice(self):
  td,r,db,bp=self.fixture();self.addCleanup(td.cleanup)
  ev=[{"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"same"},
      {"candidate_name":"AMITA VEGAN","observed_name":"ร้านอาหารเจ AMITA VEGAN","province":"ปราจีนบุรี","source_family":"same"}]
  x=self.execute(r,db,bp,ev);self.assertEqual(x["decisions"][0]["identity_outcome"],"SUPPORTED_IDENTITY")
 def test_duplicate_phone_blocks(self):
  td,r,db,bp=self.fixture();self.addCleanup(td.cleanup);c=sqlite3.connect(db)
  c.execute("insert into places values('p','Other','เชียงใหม่','0804653226')");c.commit();c.close()
  ev=[{"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"a","phone":"0804653226"},
      {"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"b","phone":"0804653226"}]
  x=self.execute(r,db,bp,ev);self.assertEqual(x["decisions"][0]["identity_outcome"],"BLOCKED_EXISTING_CANONICAL")
 def test_verified_identity_is_not_yet_canonical_ready_without_geo(self):
  td,r,db,bp=self.fixture();self.addCleanup(td.cleanup)
  ev=[{"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"a"},
      {"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_family":"b"}]
  x=self.execute(r,db,bp,ev);self.assertFalse(x["decisions"][0]["canonical_adoption_ready"])
 def test_zero_write(self):
  td,r,db,bp=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes()
  x=self.execute(r,db,bp,[]);self.assertEqual(b,db.read_bytes());self.assertTrue(x["safety"]["database_unchanged"])
if __name__=="__main__":unittest.main()
