import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.geolocation_precanonical import verify_geolocation_and_persist
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text primary key)");c.commit();c.close()
  ident={"decisions":[{"candidate_key":"k","name":"AMITA VEGAN","province":"ปราจีนบุรี","category":"vegetarian","identity_outcome":"VERIFIED_IDENTITY","independent_source_family_count":2}]}
  ie=[{"candidate_name":"AMITA VEGAN","observed_name":"AMITA VEGAN","province":"ปราจีนบุรี","source_name":"A","source_family":"a","evidence_kind":"identity"}]
  ip=r/"i.json";ep=r/"e.json";ip.write_text(json.dumps(ident),encoding="utf-8");ep.write_text(json.dumps(ie),encoding="utf-8")
  return td,r,db,ip,ep
 def execute(self,r,db,ip,ep,g,commit=False):
  gp=r/"g.json";gp.write_text(json.dumps(g),encoding="utf-8")
  return verify_geolocation_and_persist(database_path=db,identity_report_path=ip,identity_evidence_path=ep,geolocation_observations_path=gp,commit=commit)
 def test_address_only_does_not_fake_exact_coordinates(self):
  td,r,db,ip,ep=self.fixture();self.addCleanup(td.cleanup)
  g=[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","subdistrict":"ท่าตูม","district":"ศรีมหาโพธิ","evidence_kind":"candidate_address_location"}]
  x=self.execute(r,db,ip,ep,g);d=x["results"][0]
  self.assertEqual(d["geolocation_outcome"],"ADDRESS_LOCATION_VERIFIED_COORDINATES_UNRESOLVED");self.assertFalse(d["canonical_adoption_ready"])
 def test_landmark_coordinates_never_become_candidate_coordinates(self):
  td,r,db,ip,ep=self.fixture();self.addCleanup(td.cleanup)
  g=[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","subdistrict":"ท่าตูม","district":"ศรีมหาโพธิ","evidence_kind":"candidate_address_location"},
     {"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","latitude":13.8,"longitude":101.5,"coordinate_owner":"hospital","evidence_kind":"landmark_geolocation_reference"}]
  x=self.execute(r,db,ip,ep,g);self.assertFalse(x["results"][0]["exact_coordinates_verified"])
 def test_commit_persists_precanonical_only(self):
  td,r,db,ip,ep=self.fixture();self.addCleanup(td.cleanup)
  g=[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","subdistrict":"ท่าตูม","district":"ศรีมหาโพธิ","source_name":"geo","source_family":"geo","evidence_kind":"candidate_address_location"}]
  x=self.execute(r,db,ip,ep,g,True);self.assertEqual(x["inserted_candidate_count"],1);self.assertEqual(x["precanonical_candidate_total"],1)
  self.assertTrue(x["safety"]["canonical_place_count_unchanged"])
 def test_replay_is_idempotent(self):
  td,r,db,ip,ep=self.fixture();self.addCleanup(td.cleanup)
  g=[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","subdistrict":"ท่าตูม","district":"ศรีมหาโพธิ","source_name":"geo","source_family":"geo","evidence_kind":"candidate_address_location"}]
  self.execute(r,db,ip,ep,g,True);x=self.execute(r,db,ip,ep,g,True);self.assertEqual(x["inserted_candidate_count"],0)
 def test_dry_run_zero_write(self):
  td,r,db,ip,ep=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes()
  x=self.execute(r,db,ip,ep,[]);self.assertEqual(b,db.read_bytes())
if __name__=="__main__":unittest.main()
