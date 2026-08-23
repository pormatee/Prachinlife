import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.direct_lifecycle_confirmation import evaluate_direct_confirmation
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory();root=Path(td.name);db=root/"x.sqlite3";c=sqlite3.connect(db)
  c.execute("create table places(place_id text primary key,canonical_name text)")
  c.execute("""create table precanonical_candidates(candidate_id text primary key,proposed_name text,province text)""")
  c.execute("insert into precanonical_candidates values('c1','ต้นหลิวอาหารเจ','ปราจีนบุรี')");c.commit();c.close()
  return td,root,db
 def write(self,root,**kw):
  base={"candidate_name":"ต้นหลิวอาหารเจ","province":"ปราจีนบุรี","confirmer":"operator1","confirmer_role":"operator",
        "method":"phone","result":"open","confirmed_at":"2026-08-23T11:30:00+07:00",
        "contact_or_reference":"0959176495","notes":"Direct call"}
  base.update(kw);p=root/"c.json";p.write_text(json.dumps(base),encoding="utf-8");return p
 def test_valid_open_confirmation(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r)
  x=evaluate_direct_confirmation(database_path=db,confirmation_path=p);self.assertEqual(x["confirmation_outcome"],"CONFIRMED_OPEN")
 def test_valid_closed_confirmation(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r,result="permanently_closed")
  x=evaluate_direct_confirmation(database_path=db,confirmation_path=p);self.assertEqual(x["confirmation_outcome"],"CONFIRMED_CLOSED")
 def test_missing_provenance_remains_unresolved(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r,confirmer="",confirmed_at="")
  x=evaluate_direct_confirmation(database_path=db,confirmation_path=p);self.assertEqual(x["confirmation_outcome"],"STILL_UNRESOLVED")
  self.assertTrue(x["validation_errors"])
 def test_commit_is_idempotent_and_only_writes_confirmation_table(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r)
  a=evaluate_direct_confirmation(database_path=db,confirmation_path=p,commit=True)
  b=evaluate_direct_confirmation(database_path=db,confirmation_path=p,commit=True)
  self.assertEqual(a["inserted_confirmation_count"],1);self.assertEqual(b["inserted_confirmation_count"],0)
  self.assertTrue(b["safety"]["canonical_rows_unchanged"]);self.assertTrue(b["safety"]["precanonical_candidate_rows_unchanged"])
 def test_unresolved_confirmation_never_mutates_lifecycle(self):
  td,r,db=self.fixture();self.addCleanup(td.cleanup);p=self.write(r,result="unresolved",contact_or_reference="")
  x=evaluate_direct_confirmation(database_path=db,confirmation_path=p,commit=True)
  self.assertEqual(x["confirmation_outcome"],"STILL_UNRESOLVED");self.assertTrue(x["safety"]["automatic_lifecycle_mutation"] is False)
if __name__=="__main__":unittest.main()
