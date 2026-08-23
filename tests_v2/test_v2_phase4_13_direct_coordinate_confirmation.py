import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.direct_coordinate_confirmation import confirm_direct_coordinates
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);db=r/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text primary key,canonical_name text)")
  c.execute("""create table precanonical_candidates(candidate_id text primary key,proposed_name text,province text)""")
  c.execute("insert into precanonical_candidates values('c1','ร้านอาหารเจ AMITA VEGAN','ปราจีนบุรี')");c.commit();c.close()
  return td,r,db
 def write(self,r,**kw):
  x={"candidate_name":"ร้านอาหารเจ AMITA VEGAN","province":"ปราจีนบุรี","confirmer":"op1","confirmer_role":"operator",
     "method":"map_pin","latitude":13.90,"longitude":101.60,"confirmed_at":"2026-08-23T12:00:00+07:00",
     "reference":"Google Maps pin supplied by operator","notes":"direct pin"}
  x.update(kw);p=r/"c.json";p.write_text(json.dumps(x),encoding="utf-8");return p
 def test_valid_direct_coordinate_confirmation(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r)
  x=confirm_direct_coordinates(database_path=db,confirmation_path=p);self.assertEqual(x["confirmation_outcome"],"DIRECT_COORDINATES_CONFIRMED")
 def test_missing_provenance_stays_unresolved(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r,confirmer="",reference="")
  x=confirm_direct_coordinates(database_path=db,confirmation_path=p);self.assertEqual(x["confirmation_outcome"],"STILL_UNRESOLVED")
 def test_outside_prachinburi_context_is_blocked(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r,latitude=18.7,longitude=98.9)
  x=confirm_direct_coordinates(database_path=db,confirmation_path=p);self.assertIn("outside_prachinburi_context",x["validation_errors"])
 def test_commit_idempotent_confirmation_only(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r)
  a=confirm_direct_coordinates(database_path=db,confirmation_path=p,commit=True)
  b=confirm_direct_coordinates(database_path=db,confirmation_path=p,commit=True)
  self.assertEqual(a["inserted_confirmation_count"],1);self.assertEqual(b["inserted_confirmation_count"],0)
  self.assertTrue(b["safety"]["canonical_rows_unchanged"]);self.assertTrue(b["safety"]["precanonical_candidate_rows_unchanged"])
 def test_template_never_guesses_coordinate(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r,confirmer="",confirmer_role="",method="",latitude=None,longitude=None,confirmed_at="",reference="")
  x=confirm_direct_coordinates(database_path=db,confirmation_path=p);self.assertFalse(x["coordinates_resolved"]);self.assertFalse(x["safety"]["automatic_coordinate_guessing"])
if __name__=="__main__":unittest.main()
