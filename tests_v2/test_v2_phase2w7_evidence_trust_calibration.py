import sqlite3,tempfile,unittest,uuid
from pathlib import Path
from place_platform_v2.evidence_trust_calibration import classify_evidence,calibrate_evidence_trust,database_sha256
from place_platform_v2.contracts import EvidenceStatus,GeoPoint,SourceRef,SourceType
from place_platform_v2.models import CanonicalPlace,PlaceEvidence,PlaceIdentity,PlaceLifecycle,EvidenceKind
from place_platform_v2.sqlite_store import SQLitePlaceRepository

def src(name,record=None,url=None): return SourceRef(SourceType.OTHER,name,record,url)
def ev(pid,field,value,source,md=None): return PlaceEvidence(pid,source,EvidenceKind.OTHER,field,value,EvidenceStatus.CANDIDATE,evidence_id=str(uuid.uuid4()),metadata=md or {})
class TestPhase2W7(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.db=Path(self.t.name)/'x.sqlite3'; self.r=SQLitePlaceRepository(self.db)
  self.pid=str(uuid.uuid4()); p=CanonicalPlace(identity=PlaceIdentity(self.pid), canonical_name='Pilot', location=GeoPoint(14.1,101.4), province='ปราจีนบุรี', categories=('eat',), lifecycle=PlaceLifecycle.UNKNOWN)
  self.r.save_place(p)
  for f,v in [('canonical_name','Pilot'),('location',GeoPoint(14.1,101.4)),('province','ปราจีนบุรี'),('categories',('eat',))]: self.r.add_evidence(ev(self.pid,f,v,src('prachinlife-v1-json','service_index.json#osm-node-123')))
 def tearDown(self): self.t.cleanup()
 def test_w701_v1_osm_is_classified_derived(self):
  e=ev(self.pid,'x',1,src('prachinlife-v1-json','x#osm-node-123')); self.assertEqual(classify_evidence(e),'v1_derived_osm')
 def test_w702_direct_osm_class(self):
  e=ev(self.pid,'x',1,src('OpenStreetMap',url='https://www.openstreetmap.org/node/123')); self.assertEqual(classify_evidence(e),'direct_osm')
 def test_w703_admin_operator_class(self):
  e=ev(self.pid,'x',1,src('PrachinLife Admin Operator')); self.assertEqual(classify_evidence(e),'admin_operator')
 def test_w704_osm_v1_and_direct_collapse_lineage(self):
  self.r.add_evidence(ev(self.pid,'canonical_name','Pilot',src('OpenStreetMap',url='https://www.openstreetmap.org/node/123')))
  report,rows=calibrate_evidence_trust(self.db,pilot_limit=5); row=rows[0]; self.assertEqual(row.lineage_count,1)
 def test_w705_scope_defaults_prachinburi(self):
  report,_=calibrate_evidence_trust(self.db); self.assertEqual(report.province,'ปราจีนบุรี'); self.assertEqual(report.canonical_count,1)
 def test_w706_ranking_is_not_verification(self):
  report,_=calibrate_evidence_trust(self.db); self.assertEqual(report.lifecycle_active_count,0); self.assertNotIn(('lineage_ready_shape',1),report.readiness_shape_counts)
 def test_w707_read_only_byte_stable(self):
  before=database_sha256(self.db); calibrate_evidence_trust(self.db); after=database_sha256(self.db); self.assertEqual(before,after)
if __name__=='__main__': unittest.main()
