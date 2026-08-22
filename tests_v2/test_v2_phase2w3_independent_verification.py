from __future__ import annotations
import sqlite3,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from place_platform_v2.contracts import EvidenceStatus,GeoPoint,SourceRef,SourceType
from place_platform_v2.models import CanonicalPlace,EvidenceKind,PlaceEvidence,PlaceIdentity,PlaceLifecycle
from place_platform_v2.publication_verification import make_bundle,evaluate_bundle,commit_bundle
from place_platform_v2.sqlite_store import SQLitePlaceRepository
NOW=datetime(2026,8,22,tzinfo=timezone.utc)

def seed(db):
 repo=SQLitePlaceRepository(db); p=CanonicalPlace(identity=PlaceIdentity(),canonical_name='Caltex',location=GeoPoint(13.77,102.02),province='ปราจีนบุรี',categories=('fuel',),lifecycle=PlaceLifecycle.UNKNOWN,created_at=NOW,updated_at=NOW); repo.save_place(p)
 src=SourceRef(SourceType.OSM,'OpenStreetMap',source_record_id='node-1',source_url='https://www.openstreetmap.org/node/1',observed_at=NOW)
 for f in ('canonical_name','location','province','categories'):
  repo.add_evidence(PlaceEvidence(place_id=p.identity.place_id,source=src,kind=EvidenceKind.OTHER,field_name=f,value=getattr(p,f),status=EvidenceStatus.CANDIDATE,observed_at=NOW))
 repo.close(); return p

def bundle(p,name='Caltex Official',url='https://official.example/station/1',record='station-1'):
 s=SourceRef(SourceType.OFFICIAL,name,source_record_id=record,source_url=url,observed_at=NOW)
 return make_bundle(place_id=p.identity.place_id,source=s,claims={'canonical_name':p.canonical_name,'location':p.location,'province':p.province,'categories':p.categories,'lifecycle':PlaceLifecycle.ACTIVE})
class TestW3(unittest.TestCase):
 def test_w301_dry_run_is_read_only(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); b=bundle(p); before=db.read_bytes(); r=evaluate_bundle(db,b); self.assertEqual(r.result,'ready_to_commit'); self.assertEqual(before,db.read_bytes())
 def test_w302_same_osm_lineage_is_blocked(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); s=SourceRef(SourceType.OTHER,'mirror',source_record_id='copy-osm-node-1',observed_at=NOW); b=make_bundle(place_id=p.identity.place_id,source=s,claims={'canonical_name':p.canonical_name,'location':p.location,'province':p.province,'categories':p.categories,'lifecycle':PlaceLifecycle.ACTIVE}); self.assertEqual(evaluate_bundle(db,b).result,'blocked_same_lineage')
 def test_w303_conflicting_identity_is_blocked(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); s=SourceRef(SourceType.OFFICIAL,'Official',source_record_id='9',observed_at=NOW); b=make_bundle(place_id=p.identity.place_id,source=s,claims={'canonical_name':'Other','location':p.location,'province':p.province,'categories':p.categories,'lifecycle':PlaceLifecycle.ACTIVE}); self.assertEqual(evaluate_bundle(db,b).result,'blocked_conflict')
 def test_w304_commit_adds_evidence_audit_and_activates(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); r=commit_bundle(db,bundle(p)); self.assertEqual(r.result,'committed'); self.assertFalse(r.publication_ready_after); repo=SQLitePlaceRepository(db); self.assertEqual(repo.get_place(p.identity.place_id).lifecycle,PlaceLifecycle.UNKNOWN); self.assertEqual(len(repo.list_evidence(p.identity.place_id)),9); repo.close(); con=sqlite3.connect(db); self.assertEqual(con.execute('SELECT COUNT(*) FROM publication_verification_bundles').fetchone()[0],1); con.close()
 def test_w305_second_independent_bundle_reaches_quorum_and_activates(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); a=commit_bundle(db,bundle(p)); b2=bundle(p,name='Field Verification',url='https://field.example/visit/2',record='visit-2'); c=commit_bundle(db,b2); self.assertEqual(a.lifecycle_after,'unknown'); self.assertEqual(c.lifecycle_after,'active'); self.assertTrue(c.publication_ready_after)
 def test_w306_commit_is_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); b=bundle(p); a=commit_bundle(db,b); c=commit_bundle(db,b); self.assertEqual(a.result,'committed'); self.assertEqual(c.result,'already_committed')
if __name__=='__main__': unittest.main()
