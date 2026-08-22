from __future__ import annotations
import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from place_platform_v2.models import CanonicalPlace, EvidenceKind, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from place_platform_v2.publication_readiness import evidence_lineage_key, evaluate_pilot_readiness
from place_platform_v2.sqlite_store import SQLitePlaceRepository
NOW=datetime(2026,8,22,tzinfo=timezone.utc)

def ev(pid,field,value,name,record,url=None):
 return PlaceEvidence(place_id=pid,source=SourceRef(SourceType.OTHER,name,source_record_id=record,source_url=url,observed_at=NOW),kind=EvidenceKind.OTHER,field_name=field,value=value,status=EvidenceStatus.CANDIDATE,observed_at=NOW)

def seed(db, same_lineage=False, lifecycle=PlaceLifecycle.ACTIVE):
 repo=SQLitePlaceRepository(db); p=CanonicalPlace(identity=PlaceIdentity(),canonical_name='X',location=GeoPoint(14,101),province='ปราจีนบุรี',categories=('fuel',),lifecycle=lifecycle,created_at=NOW,updated_at=NOW); repo.save_place(p)
 for f in ('canonical_name','location','province','categories','lifecycle'):
  v=getattr(p,f); repo.add_evidence(ev(p.identity.place_id,f,v,'OpenStreetMap','node-123','https://www.openstreetmap.org/node/123'))
  if same_lineage: repo.add_evidence(ev(p.identity.place_id,f,v,'prachinlife-v1-json','service.json#osm-node-123'))
  else: repo.add_evidence(ev(p.identity.place_id,f,v,'Official Registry',f'official-{f}','https://official.example/place/9'))
 repo.close(); return p

class TestW2(unittest.TestCase):
 def test_w201_osm_and_v1_osm_collapse_same_lineage(self):
  a=ev(PlaceIdentity().place_id,'x','y','prachinlife-v1-json','service.json#osm-node-123')
  b=ev(a.place_id,'x','y','OpenStreetMap','node-123','https://www.openstreetmap.org/node/123')
  self.assertEqual(evidence_lineage_key(a),evidence_lineage_key(b))
 def test_w202_true_independent_sources_are_ready(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); r=evaluate_pilot_readiness(db,p.identity.place_id); self.assertTrue(r.publication_ready); self.assertEqual(len(r.blocked_fields),0)
 def test_w203_same_lineage_does_not_fake_verification(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db,True); r=evaluate_pilot_readiness(db,p.identity.place_id); self.assertFalse(r.publication_ready); self.assertIn('canonical_name',r.blocked_fields)
 def test_w204_unknown_lifecycle_blocks_even_with_sources(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db,False,PlaceLifecycle.UNKNOWN); r=evaluate_pilot_readiness(db,p.identity.place_id); self.assertFalse(r.publication_ready); self.assertIn('canonical lifecycle is not active',r.reasons)
 def test_w205_readiness_is_byte_read_only(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.db'; p=seed(db); before=db.read_bytes(); evaluate_pilot_readiness(db,p.identity.place_id); self.assertEqual(before,db.read_bytes())
if __name__=='__main__': unittest.main()
