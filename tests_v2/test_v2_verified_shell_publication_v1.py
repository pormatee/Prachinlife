from __future__ import annotations
import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.web_export import export_prachinlife_json

SCHEMA='''
CREATE TABLE places(place_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,latitude REAL,longitude REAL,address_text TEXT,province TEXT,categories_json TEXT NOT NULL,phone TEXT,website TEXT,lifecycle TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE place_evidence(evidence_id TEXT PRIMARY KEY,place_id TEXT NOT NULL,source_type TEXT,source_name TEXT,source_record_id TEXT,source_url TEXT,source_observed_at TEXT,kind TEXT,field_name TEXT,value_json TEXT,status TEXT,observed_at TEXT,metadata_json TEXT);
CREATE TABLE place_revisions(revision_id TEXT PRIMARY KEY,place_id TEXT NOT NULL,changed_fields_json TEXT NOT NULL,before_values_json TEXT NOT NULL,after_values_json TEXT NOT NULL,reason TEXT NOT NULL,evidence_ids_json TEXT NOT NULL,policy_version TEXT NOT NULL,created_at TEXT NOT NULL);
'''
class VerifiedShellPublicationV1(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.db=Path(self.t.name)/'db.sqlite3'; self.out=Path(self.t.name)/'out.json'
  con=sqlite3.connect(self.db); con.executescript(SCHEMA)
  def add(pid,name,lat,lon,state,category):
   con.execute("insert into places values(?,?,?,?,?,?,?,?,?,?,?,?)",(pid,name,lat,lon,None,'ปทุมธานี',json.dumps([category]),None,None,'unknown','2026-08-25T00:00:00+00:00','2026-08-25T00:00:00+00:00'))
   if state: con.execute("insert into place_revisions values(?,?,?,?,?,?,?,?,?)",('r-'+pid,pid,'[]','{}',json.dumps({'core_v2_state':state}),'state','[]','test','2026-08-25T00:00:00+00:00'))
  add('pending','Baan J Veggie House',None,None,'VERIFIED_PLACE_COORDINATE_PENDING','vegetarian')
  add('unsafe','Unverified Null Place',None,None,None,'service')
  add('ready','Ready Place',14.1,100.1,'VERIFIED_NEAR_ME_READY','shopping')
  con.commit(); con.close()
 def tearDown(self): self.t.cleanup()
 def test_verified_pending_shell_is_public_but_not_near_me(self):
  p=export_prachinlife_json(self.db,self.out,province='ปทุมธานี'); by={x['id']:x for x in p['places']}
  self.assertIn('pending',by); self.assertNotIn('unsafe',by); self.assertIn('ready',by)
  self.assertTrue(by['pending']['verified_place']); self.assertFalse(by['pending']['near_me_eligible']); self.assertEqual(by['pending']['coordinate_status'],'pending_review'); self.assertIsNone(by['pending']['latitude']); self.assertIsNone(by['pending']['longitude'])
  self.assertTrue(by['ready']['near_me_eligible'])
 def test_adapter_supports_pending_without_fake_zero_coordinates(self):
  t=Path('js/core/v2-place-adapter.js').read_text(encoding='utf-8')
  self.assertIn('coordinateValuesPresent',t); self.assertIn('near_me_eligible',t); self.assertIn('coordinate_pending',t)
  self.assertNotIn('if (!name || !Number.isFinite(latitude) || !Number.isFinite(longitude))',t)
if __name__=='__main__': unittest.main()
