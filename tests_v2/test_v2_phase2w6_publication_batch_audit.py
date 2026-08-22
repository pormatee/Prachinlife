import tempfile, unittest
from pathlib import Path
from uuid import uuid4
from place_platform_v2.publication_batch_audit import audit_publication_readiness
from place_platform_v2.sqlite_store import SQLitePlaceRepository
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle, PlaceEvidence, EvidenceKind
from place_platform_v2.contracts import GeoPoint, SourceRef, EvidenceStatus, SourceType

class T(unittest.TestCase):
 def seed(self):
  td=tempfile.TemporaryDirectory(); db=Path(td.name)/'x.sqlite3'; repo=SQLitePlaceRepository(db)
  pid=str(uuid4()); p=CanonicalPlace(PlaceIdentity(pid), 'A', GeoPoint(14,101), None, 'ปราจีนบุรี', ('fuel',), lifecycle=PlaceLifecycle.UNKNOWN); repo.save_place(p)
  for n in (1,2):
   s=SourceRef(SourceType.MANUAL,f'S{n}',source_record_id=f'r{n}')
   for f,v in [('canonical_name','A'),('location',p.location),('province','ปราจีนบุรี'),('categories',('fuel',))]: repo.add_evidence(PlaceEvidence(pid,s,EvidenceKind.OTHER,f,v,EvidenceStatus.SUPPORTED))
  repo.close(); return td,db,pid
 def test_batch_is_read_only(self):
  td,db,_=self.seed(); before=db.read_bytes(); audit_publication_readiness(db); self.assertEqual(before,db.read_bytes()); td.cleanup()
 def test_unknown_lifecycle_blocks(self):
  td,db,pid=self.seed(); r,rows=audit_publication_readiness(db); x=next(x for x in rows if x.place_id==pid); self.assertEqual(x.bucket,'needs_lifecycle'); self.assertEqual(x.blocked_fields,('lifecycle',)); td.cleanup()
 def test_counts_cover_all_places(self):
  td,db,_=self.seed(); r,rows=audit_publication_readiness(db); self.assertEqual(r.canonical_count,len(rows)); self.assertEqual(r.ready_count+r.blocked_count,r.canonical_count); td.cleanup()
 def test_pilots_rank_fewest_blockers(self):
  td,db,_=self.seed(); r,_=audit_publication_readiness(db,pilot_limit=1); self.assertEqual(len(r.pilot_candidates),1); self.assertEqual(r.pilot_candidates[0].blocker_count,1); td.cleanup()
 def test_no_publication_side_effect_flag(self):
  td,db,_=self.seed(); r,_=audit_publication_readiness(db); self.assertFalse(r.publication_performed); self.assertFalse(r.user_web_switched); td.cleanup()
 def test_field_counts_expose_lifecycle_gap(self):
  td,db,_=self.seed(); r,_=audit_publication_readiness(db); self.assertEqual(dict(r.field_block_counts)['lifecycle'],1); td.cleanup()

if __name__=='__main__': unittest.main()
