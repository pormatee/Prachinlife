import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.new_place_adoption_machine import evaluate_new_place_adoption,run_controlled_new_place_adoption
class T(unittest.TestCase):
 def db(self,ready=True):
  td=tempfile.TemporaryDirectory();p=Path(td.name)/'x.db';c=sqlite3.connect(p)
  c.executescript('''create table places(place_id text primary key,canonical_name text not null,latitude real,longitude real,address_text text,province text,categories_json text not null,phone text,website text,lifecycle text not null,created_at text not null,updated_at text not null);create table place_evidence(evidence_id text primary key,place_id text not null,source_type text not null,source_name text not null,source_record_id text,source_url text,source_observed_at text not null,kind text not null,field_name text not null,value_json text not null,status text not null,observed_at text not null,metadata_json text not null);create table place_revisions(revision_id text primary key,place_id text not null,changed_fields_json text not null,before_values_json text not null,after_values_json text not null,reason text not null,evidence_ids_json text not null,policy_version text not null,created_at text not null);create table precanonical_candidates(candidate_id text primary key,candidate_key text,proposed_name text,province text,category text,identity_outcome text,independent_source_family_count integer,lifecycle_conflict_json text,status text,policy_version text,created_at text);create table precanonical_evidence(evidence_id text primary key,candidate_id text,source_type text,source_name text,source_family text,source_record_id text,source_url text,observed_name text,province text,phone text,website text,lifecycle_status text,evidence_kind text,payload_json text,policy_version text,created_at text);''')
  c.execute("insert into precanonical_candidates values('c','k','ร้านเจทดสอบ','ปราจีนบุรี','vegetarian','VERIFIED_IDENTITY',2,'[]','verified','p','t')")
  for i,f in enumerate(['a','b']):
   payload={'address_text':'ท่าตูม ปราจีนบุรี'}
   if ready and i==0:payload.update(latitude=13.9,longitude=101.6,coordinate_owner='candidate')
   c.execute('insert into precanonical_evidence values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'e{i}','c','web',f,f,None,f'https://{f}','ร้านเจทดสอบ','ปราจีนบุรี','0800000000',None,'open','candidate_address_location' if i==0 else 'identity',json.dumps(payload),'p','t'))
  c.commit();c.close();return td,p
 def test_ready_gate(self):
  td,p=self.db();self.addCleanup(td.cleanup);r=evaluate_new_place_adoption(database_path=p);self.assertEqual(r['ready_count'],1)
 def test_missing_coords_not_ready(self):
  td,p=self.db(False);self.addCleanup(td.cleanup);r=evaluate_new_place_adoption(database_path=p);self.assertIn('exact_candidate_coordinates_not_verified',r['decisions'][0]['blockers'])
 def test_dry_run_zero_write(self):
  td,p=self.db();self.addCleanup(td.cleanup);b=p.read_bytes();r=run_controlled_new_place_adoption(database_path=p);self.assertEqual(b,p.read_bytes());self.assertEqual(r['eligible_count'],1)
 def test_commit_creates_canonical_and_evidence(self):
  td,p=self.db();self.addCleanup(td.cleanup);r=run_controlled_new_place_adoption(database_path=p,commit=True);self.assertEqual(r['inserted_place_count'],1);c=sqlite3.connect(p);self.assertEqual(c.execute('select count(*) from places').fetchone()[0],1);self.assertGreater(c.execute('select count(*) from place_evidence').fetchone()[0],0);c.close()
 def test_commit_idempotent(self):
  td,p=self.db();self.addCleanup(td.cleanup);run_controlled_new_place_adoption(database_path=p,commit=True);r=run_controlled_new_place_adoption(database_path=p,commit=True);self.assertEqual(r['inserted_place_count'],0)
if __name__=='__main__':unittest.main()
