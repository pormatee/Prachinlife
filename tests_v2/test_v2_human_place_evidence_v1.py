from __future__ import annotations
import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.human_place_evidence import (
    PENDING_STATE, READY_STATE, apply_approved_coordinate_evidence,
    review_coordinate_evidence, submit_coordinate_evidence,
)

SCHEMA='''
CREATE TABLE places(place_id TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,latitude REAL,longitude REAL,address_text TEXT,province TEXT,categories_json TEXT NOT NULL,phone TEXT,website TEXT,lifecycle TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE place_evidence(evidence_id TEXT PRIMARY KEY,place_id TEXT NOT NULL,source_type TEXT,source_name TEXT,source_record_id TEXT,source_url TEXT,source_observed_at TEXT,kind TEXT,field_name TEXT,value_json TEXT,status TEXT,observed_at TEXT,metadata_json TEXT);
CREATE TABLE place_revisions(revision_id TEXT PRIMARY KEY,place_id TEXT NOT NULL,changed_fields_json TEXT NOT NULL,before_values_json TEXT NOT NULL,after_values_json TEXT NOT NULL,reason TEXT NOT NULL,evidence_ids_json TEXT NOT NULL,policy_version TEXT NOT NULL,created_at TEXT NOT NULL);
'''

class HumanEvidenceV1(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.db=Path(self.t.name)/'db.sqlite3'
        con=sqlite3.connect(self.db); con.executescript(SCHEMA)
        con.execute("insert into places values(?,?,?,?,?,?,?,?,?,?,?,?)",('baanj','Baan J Veggie House',None,None,None,'ปทุมธานี',json.dumps(['vegetarian']),'','','unknown','2026-08-25T00:00:00+00:00','2026-08-25T00:00:00+00:00'))
        con.execute("insert into place_revisions values(?,?,?,?,?,?,?,?,?)",('r0','baanj',json.dumps(['create_place']),json.dumps({}),json.dumps({'core_v2_state':PENDING_STATE}), 'core v2 shell',json.dumps([]),'core-v2','2026-08-25T00:00:00+00:00'))
        con.commit(); con.close()
    def tearDown(self): self.t.cleanup()
    def submit(self):
        return submit_coordinate_evidence(database_path=self.db,place_id='baanj',latitude=14.12345,longitude=100.54321,source_kind='user',source_name='TEST_ONLY_USER_FIXTURE',evidence_note='TEST_ONLY exact candidate pin')
    def test_submission_never_changes_canonical_coordinates(self):
        r=self.submit(); self.assertEqual(r['status'],'PENDING_REVIEW'); self.assertFalse(r['near_me_enabled'])
        con=sqlite3.connect(self.db); self.assertEqual(con.execute("select latitude,longitude from places where place_id='baanj'").fetchone(),(None,None)); con.close()
    def test_unreviewed_cannot_apply(self):
        sid=self.submit()['submission_id']
        with self.assertRaises(ValueError): apply_approved_coordinate_evidence(database_path=self.db,submission_id=sid,commit=True)
    def test_approval_requires_owner_confirmation(self):
        sid=self.submit()['submission_id']
        with self.assertRaises(ValueError): review_coordinate_evidence(database_path=self.db,submission_id=sid,approve=True,reviewer='admin',review_note='reviewed',review_basis='user_evidence_admin_review',coordinate_owner_confirmed=False)
    def test_approved_dry_run_then_controlled_apply(self):
        sid=self.submit()['submission_id']
        review_coordinate_evidence(database_path=self.db,submission_id=sid,approve=True,reviewer='admin-test',review_note='TEST_ONLY reviewed exact pin',review_basis='user_evidence_admin_review',coordinate_owner_confirmed=True)
        dry=apply_approved_coordinate_evidence(database_path=self.db,submission_id=sid,commit=False)
        self.assertEqual(dry['status'],'READY_TO_APPLY'); self.assertTrue(dry['database_unchanged']); self.assertFalse(dry['near_me_eligible'])
        out=apply_approved_coordinate_evidence(database_path=self.db,submission_id=sid,commit=True)
        self.assertEqual(out['state_after'],READY_STATE); self.assertTrue(out['near_me_eligible']); self.assertFalse(out['automatic_publication'])
        con=sqlite3.connect(self.db); lat,lon=con.execute("select latitude,longitude from places where place_id='baanj'").fetchone(); self.assertAlmostEqual(lat,14.12345); self.assertAlmostEqual(lon,100.54321)
        md=json.loads(con.execute("select metadata_json from place_evidence where place_id='baanj' and field_name='location'").fetchone()[0]); self.assertTrue(md['coordinate_owner_confirmed']); con.close()
    def test_category_agnostic_no_category_branch(self):
        text=Path('place_platform_v2/human_place_evidence.py').read_text(encoding='utf-8')
        for category in ('eat','travel','service','shopping','vegetarian'):
            self.assertNotIn(f'category == "{category}"',text)

if __name__=='__main__': unittest.main()
