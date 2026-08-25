from __future__ import annotations
import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.controlled_new_place_adoption_core_v2 import (
    evaluate_controlled_new_place_adoption_core_v2,
    run_controlled_new_place_adoption_core_v2,
)

class T(unittest.TestCase):
 def db(self):
  td=tempfile.TemporaryDirectory();db=Path(td.name)/'x.db';c=sqlite3.connect(db)
  c.executescript('''create table places(place_id text primary key,canonical_name text not null,latitude real,longitude real,address_text text,province text,categories_json text not null,phone text,website text,lifecycle text not null,created_at text not null,updated_at text not null);create table place_evidence(evidence_id text primary key,place_id text not null,source_type text not null,source_name text not null,source_record_id text,source_url text,source_observed_at text not null,kind text not null,field_name text not null,value_json text not null,status text not null,observed_at text not null,metadata_json text not null);create table place_revisions(revision_id text primary key,place_id text not null,changed_fields_json text not null,before_values_json text not null,after_values_json text not null,reason text not null,evidence_ids_json text not null,policy_version text not null,created_at text not null);create table precanonical_candidates(candidate_id text primary key,candidate_key text,proposed_name text,province text,category text,identity_outcome text,independent_source_family_count integer,lifecycle_conflict_json text,status text,policy_version text,created_at text);create table precanonical_evidence(evidence_id text primary key,candidate_id text,source_type text,source_name text,source_family text,source_record_id text,source_url text,observed_name text,province text,phone text,website text,lifecycle_status text,evidence_kind text,payload_json text,policy_version text,created_at text);''')
  for cid,name in [('a','A Vegan'),('b','B Vegan')]:
   c.execute('insert into precanonical_candidates values(?,?,?,?,?,?,?,?,?,?,?)',(cid,cid,name,'ปทุมธานี','vegetarian','VERIFIED_IDENTITY',2,'[]','verified','p','t'))
   for i,f in enumerate(['s1','s2']):
    c.execute('insert into precanonical_evidence values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'{cid}{i}',cid,'web',f,f,None,f'https://{f}',name,'ปทุมธานี',None,None,None,'identity','{}','p','t'))
  c.commit();c.close()
  report=Path(td.name)/'coords.json';report.write_text(json.dumps({'results':[{'candidate_key':'a','name':'A Vegan','province':'ปทุมธานี','coordinate_outcome':'EXACT_COORDINATES_VERIFIED','latitude':14.1,'longitude':100.6,'accepted_source_families':['osm']},{'candidate_key':'b','name':'B Vegan','province':'ปทุมธานี','coordinate_outcome':'EXACT_COORDINATES_UNRESOLVED','latitude':None,'longitude':None,'accepted_source_families':[]}]}),encoding='utf-8')
  return td,db,report
 def test_core_v2_dry_run_allows_coordinate_pending_canonical_shell(self):
  td,db,r=self.db();self.addCleanup(td.cleanup);x=evaluate_controlled_new_place_adoption_core_v2(database_path=db,coordinate_report_paths=[r]);self.assertEqual(2,x['canonical_eligible_count']);self.assertEqual(1,x['near_me_ready_count']);self.assertEqual(1,x['coordinate_pending_count'])
 def test_commit_creates_null_coordinate_shell_for_pending(self):
  td,db,r=self.db();self.addCleanup(td.cleanup);x=run_controlled_new_place_adoption_core_v2(database_path=db,coordinate_report_paths=[r],commit=True);self.assertEqual(2,x['inserted_place_count']);c=sqlite3.connect(db);rows={n:(lat,lon) for n,lat,lon in c.execute('select canonical_name,latitude,longitude from places')};c.close();self.assertEqual((14.1,100.6),rows['A Vegan']);self.assertEqual((None,None),rows['B Vegan'])
 def test_dry_run_zero_write(self):
  td,db,r=self.db();self.addCleanup(td.cleanup);b=db.read_bytes();x=run_controlled_new_place_adoption_core_v2(database_path=db,coordinate_report_paths=[r]);self.assertEqual(b,db.read_bytes());self.assertTrue(x['safety']['database_unchanged'])
 def test_explicit_commit_only_and_no_publication(self):
  td,db,r=self.db();self.addCleanup(td.cleanup);x=run_controlled_new_place_adoption_core_v2(database_path=db,coordinate_report_paths=[r]);self.assertTrue(x['safety']['explicit_commit_required']);self.assertFalse(x['safety']['automatic_publication']);self.assertFalse(x['safety']['trust_policy_lowered'])
if __name__=='__main__':unittest.main()
