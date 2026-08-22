from __future__ import annotations
import tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from place_platform_v2.models import CanonicalPlace, EvidenceKind, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from place_platform_v2.publication_confidence import evaluate_place, audit_database
from place_platform_v2.sqlite_store import SQLitePlaceRepository
NOW=datetime(2026,8,22,tzinfo=timezone.utc)
def ev(pid,field,value,name='OpenStreetMap',rec=None):
 return PlaceEvidence(place_id=pid,source=SourceRef(SourceType.OTHER,name,source_record_id=rec,observed_at=NOW),kind=EvidenceKind.OTHER,field_name=field,value=value,status=EvidenceStatus.CANDIDATE,observed_at=NOW)
def place(life=PlaceLifecycle.UNKNOWN):
 return CanonicalPlace(identity=PlaceIdentity(),canonical_name='ร้านเล็ก',location=GeoPoint(14,101),province='ปราจีนบุรี',categories=('eat',),lifecycle=life,created_at=NOW,updated_at=NOW)
def core(p):
 return [ev(p.identity.place_id,f,getattr(p,f),rec='osm-node-1') for f in ('canonical_name','location','province','categories')]
class T(unittest.TestCase):
 def test_w801_website_not_required(self):
  p=place(PlaceLifecycle.ACTIVE); e=core(p)+[ev(p.identity.place_id,'lifecycle',PlaceLifecycle.ACTIVE,'PrachinLife Admin Operator','admin:1')]
  self.assertEqual(evaluate_place(p,e).outcome,'eligible')
 def test_w802_core_one_lineage_can_be_supported_without_false_two_source_claim(self):
  p=place(); d=evaluate_place(p,core(p)); self.assertEqual(d.outcome,'needs_lifecycle'); self.assertEqual(set(d.core_supported),{'canonical_name','location','province','categories'})
 def test_w803_lifecycle_never_inferred_from_identity(self):
  p=place(); d=evaluate_place(p,core(p)); self.assertIn('no trusted explicit existence/lifecycle evidence',d.reasons)
 def test_w804_conflicting_core_field_requires_review(self):
  p=place(); e=core(p)+[ev(p.identity.place_id,'province','สระแก้ว','Independent','x')]; self.assertEqual(evaluate_place(p,e).outcome,'review')
 def test_w805_optional_unverified_data_does_not_block_place(self):
  p=CanonicalPlace(identity=PlaceIdentity(),canonical_name='ร้านเล็ก',location=GeoPoint(14,101),province='ปราจีนบุรี',categories=('eat',),phone='123',lifecycle=PlaceLifecycle.ACTIVE,created_at=NOW,updated_at=NOW)
  e=core(p)+[ev(p.identity.place_id,'lifecycle',PlaceLifecycle.ACTIVE,'PrachinLife Admin Operator','admin:1')]
  d=evaluate_place(p,e); self.assertEqual(d.outcome,'eligible'); self.assertNotIn('phone',d.optional_publishable)
 def test_w806_audit_is_byte_read_only(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; r=SQLitePlaceRepository(db); p=place(); r.save_place(p)
   for x in core(p): r.add_evidence(x)
   r.close(); before=db.read_bytes(); audit_database(db); self.assertEqual(before,db.read_bytes())
 def test_w807_no_publication_side_effect_claims(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; r=SQLitePlaceRepository(db); p=place(); r.save_place(p); r.close(); x=audit_database(db); self.assertFalse(x['publication_performed']); self.assertFalse(x['user_web_switched'])
if __name__=='__main__': unittest.main()
