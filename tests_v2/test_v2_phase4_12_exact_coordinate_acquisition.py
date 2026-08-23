import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.exact_coordinate_acquisition import acquire_exact_coordinates
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text)");c.commit();c.close()
  gp=r/"g.json";gp.write_text(json.dumps({"results":[{"candidate_key":"k","name":"AMITA VEGAN","province":"ปราจีนบุรี"}]}),encoding="utf-8")
  return td,r,db,gp
 def execute(self,r,db,gp,obs):
  p=r/"o.json";p.write_text(json.dumps(obs),encoding="utf-8")
  return acquire_exact_coordinates(database_path=db,geolocation_report_path=gp,observations_path=p)
 def test_landmark_coordinate_is_rejected(self):
  td,r,db,gp=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,gp,[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","coordinate_owner":"landmark","latitude":13.9,"longitude":101.6}])
  self.assertEqual(x["results"][0]["coordinate_outcome"],"EXACT_COORDINATES_UNRESOLVED")
 def test_candidate_coordinate_can_verify(self):
  td,r,db,gp=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,gp,[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","coordinate_owner":"candidate","source_family":"a","latitude":13.9,"longitude":101.6}])
  self.assertEqual(x["results"][0]["coordinate_outcome"],"EXACT_COORDINATES_VERIFIED")
 def test_conflicting_candidate_coordinates_are_blocked(self):
  td,r,db,gp=self.fixture();self.addCleanup(td.cleanup)
  obs=[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","coordinate_owner":"candidate","source_family":"a","latitude":13.9,"longitude":101.6},
       {"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","coordinate_owner":"candidate","source_family":"b","latitude":13.91,"longitude":101.61}]
  x=self.execute(r,db,gp,obs);self.assertEqual(x["results"][0]["coordinate_outcome"],"COORDINATE_CONFLICT_REVIEW_REQUIRED")
 def test_missing_numeric_coordinates_stay_unresolved(self):
  td,r,db,gp=self.fixture();self.addCleanup(td.cleanup)
  x=self.execute(r,db,gp,[{"candidate_name":"AMITA VEGAN","province":"ปราจีนบุรี","coordinate_owner":"candidate","latitude":None,"longitude":None}])
  self.assertEqual(x["results"][0]["coordinate_outcome"],"EXACT_COORDINATES_UNRESOLVED")
 def test_zero_write(self):
  td,r,db,gp=self.fixture();self.addCleanup(td.cleanup);b=db.read_bytes()
  x=self.execute(r,db,gp,[]);self.assertEqual(b,db.read_bytes());self.assertTrue(x["safety"]["database_unchanged"])
if __name__=="__main__":unittest.main()
