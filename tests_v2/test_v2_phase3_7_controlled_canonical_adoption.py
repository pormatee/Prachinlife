import json,sqlite3,tempfile,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
from place_platform_v2.controlled_canonical_adoption import apply_controlled_canonical_adoption
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace,PlaceIdentity,PlaceLifecycle
from place_platform_v2.sqlite_store import SQLitePlaceRepository
NOW=datetime(2026,8,23,tzinfo=timezone.utc)
class T(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.db=Path(self.t.name)/'d.sqlite3'; repo=SQLitePlaceRepository(self.db); self.pid=str(uuid.uuid4()); repo.save_place(CanonicalPlace(identity=PlaceIdentity(self.pid),canonical_name='T',location=GeoPoint(13,100),province='X',categories=('eat',),lifecycle=PlaceLifecycle.ACTIVE,created_at=NOW,updated_at=NOW)); repo.close(); self.add('phone','021234567','A')
 def tearDown(self): self.t.cleanup()
 def add(self,field,val,src,status='supported'):
  con=sqlite3.connect(self.db); con.execute('''insert into place_evidence(evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json) values(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(str(uuid.uuid4()),self.pid,'web',src,src,'https://x/'+src,NOW.isoformat(),'contact',field,json.dumps(val),status,NOW.isoformat(),json.dumps({'persistence':'phase3_5_controlled_web_evidence'}))); con.commit(); con.close()
 def test_dry_run_zero_write(self):
  before=self.db.read_bytes(); r=apply_controlled_canonical_adoption(database_path=self.db); self.assertEqual(before,self.db.read_bytes()); self.assertEqual(r['apply_outcome_counts'],{'ready':1})
 def test_commit_updates_and_revision(self):
  r=apply_controlled_canonical_adoption(database_path=self.db,commit=True,applied_at=NOW); self.assertEqual(r['updated_field_count'],1); con=sqlite3.connect(self.db); self.assertEqual(con.execute('select phone from places').fetchone()[0],'021234567'); self.assertEqual(con.execute('select count(*) from place_revisions').fetchone()[0],1); con.close()
 def test_idempotent(self):
  apply_controlled_canonical_adoption(database_path=self.db,commit=True,applied_at=NOW); r=apply_controlled_canonical_adoption(database_path=self.db,commit=True,applied_at=NOW); self.assertEqual(r['updated_field_count'],0); self.assertEqual(r['already_applied_count'],1)
 def test_evidence_unchanged(self):
  con=sqlite3.connect(self.db); b=con.execute('select * from place_evidence').fetchall(); con.close(); r=apply_controlled_canonical_adoption(database_path=self.db,commit=True,applied_at=NOW); self.assertTrue(r['safety']['evidence_unchanged']); con=sqlite3.connect(self.db); self.assertEqual(b,con.execute('select * from place_evidence').fetchall()); con.close()
 def test_conflict_blocks_all_writes(self):
  self.add('phone','029999999','B'); before=self.db.read_bytes(); r=apply_controlled_canonical_adoption(database_path=self.db,commit=True,applied_at=NOW); self.assertEqual(r['proposal_count'],0); self.assertEqual(before,self.db.read_bytes())
 def test_no_publication_and_policy_unchanged(self):
  r=apply_controlled_canonical_adoption(database_path=self.db); self.assertFalse(r['safety']['production_json_writes']); self.assertFalse(r['safety']['automatic_publication']); self.assertFalse(r['safety']['trust_policy_lowered'])
 def test_province_agnostic(self): self.assertTrue(apply_controlled_canonical_adoption(database_path=self.db)['safety']['province_agnostic'])
if __name__=='__main__': unittest.main()
