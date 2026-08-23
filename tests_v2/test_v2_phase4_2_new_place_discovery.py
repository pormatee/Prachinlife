import sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.new_place_discovery import *
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();p=Path(td.name)/"x.sqlite3";c=sqlite3.connect(p)
  c.execute("create table places(place_id text,canonical_name text,province text,latitude real,longitude real,phone text,website text)")
  c.execute("insert into places values(?,?,?,?,?,?,?)",("p1","อาหารเจ ซั่นสี่","ปราจีนบุรี",14.05236,101.36833,None,None));c.commit();c.close();return td,p
 def el(self,i,name,lat,lon,tags=None):
  t={"name":name};t.update(tags or {});return {"type":"node","id":i,"lat":lat,"lon":lon,"tags":t}
 def test_query_is_strict_and_province_parameterized(self):
  q=build_osm_vegetarian_query("TH-25");self.assertIn("TH-25",q);self.assertIn("diet:vegetarian",q);self.assertIn("มังสวิรัติ",q)
 def test_new_candidate_is_candidate_only(self):
  td,p=self.fixture();self.addCleanup(td.cleanup);b=p.read_bytes()
  r=discover_new_vegetarian_candidates(p,[self.el(2,"ต้นหลิวอาหารเจ",14.2,101.7)])
  self.assertEqual(r["new_place_candidate_count"],1);self.assertTrue(r["candidate_only"]);self.assertEqual(b,p.read_bytes())
 def test_existing_duplicate_is_not_new(self):
  td,p=self.fixture();self.addCleanup(td.cleanup)
  r=discover_new_vegetarian_candidates(p,[self.el(3,"อาหารเจ ซั่นสี่",14.05236,101.36833,{"diet:vegetarian":"only"})])
  self.assertEqual(r["new_place_candidate_count"],0);self.assertEqual(r["existing_place_match_count"],1)
 def test_generic_restaurant_without_diet_signal_is_excluded(self):
  td,p=self.fixture();self.addCleanup(td.cleanup)
  r=discover_new_vegetarian_candidates(p,[self.el(4,"ร้านข้าวอร่อย",14.3,101.8,{"amenity":"restaurant"})])
  self.assertEqual(r["source_observation_count"],0)
 def test_nearby_unrelated_business_is_not_false_duplicate(self):
  td,p=self.fixture();self.addCleanup(td.cleanup)
  r=discover_new_vegetarian_candidates(p,[self.el(8,"มังสวิรัติบ้านผัก",14.0524,101.3684)])
  self.assertEqual(r["new_place_candidate_count"],1);self.assertEqual(r["review_count"],0)
 def test_normalized_web_observation_preserves_provenance(self):
  td,p=self.fixture();self.addCleanup(td.cleanup)
  o={"source_type":"web","source_name":"Directory","source_record_id":"x","source_url":"https://example.test/x",
     "name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","latitude":14.2,"longitude":101.7,
     "discovery_reasons":["source_lists_as_jay_vegetarian"]}
  r=discover_new_vegetarian_candidates(p,[o]);self.assertEqual(r["new_place_candidates"][0]["source_name"],"Directory")
 def test_safety(self):
  td,p=self.fixture();self.addCleanup(td.cleanup);r=discover_new_vegetarian_candidates(p,[])
  self.assertTrue(r["safety"]["database_unchanged"]);self.assertFalse(r["safety"]["canonical_writes"]);self.assertFalse(r["safety"]["trust_policy_lowered"])
if __name__=="__main__":unittest.main()
