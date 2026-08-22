from __future__ import annotations
import shutil, sqlite3, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from place_platform_v2.discovery_persistence import persist_resolution_report
from place_platform_v2.discovery_resolution import CanonicalResolutionOrchestrator
from place_platform_v2.ingestion import DiscoveryIngestionPipeline, DiscoveryRequest
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.osm_adapter import OSMPlaceAdapterV2
from place_platform_v2.web_export import export_prachinlife_json

NOW = datetime(2026,8,21,tzinfo=timezone.utc)
DB = Path("data/v2/place_platform_v2.sqlite3")

def elem(i,name,lat=None,lon=None,province="ปราจีนบุรี"):
    tags={"name":name,"amenity":"restaurant"}
    if province is not None: tags["addr:province"]=province
    x={"type":"node","id":i,"tags":tags}
    if lat is not None: x["lat"],x["lon"]=lat,lon
    return x

def ingest(*xs):
    return DiscoveryIngestionPipeline().ingest(
        OSMPlaceAdapterV2(xs, observed_at=NOW),
        DiscoveryRequest("phase2c"),
    )

def counts(path):
    con=sqlite3.connect(path)
    try:
        return (
            con.execute("SELECT COUNT(*) FROM places").fetchone()[0],
            con.execute("SELECT COUNT(*) FROM place_evidence").fetchone()[0],
        )
    finally:
        con.close()

class TestPhase2C(unittest.TestCase):
    def test_c01_idempotent_new(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"db.sqlite3"; shutil.copy2(DB,db)
            report=CanonicalResolutionOrchestrator().resolve_report(
                ingest(elem(99990001,"Phase2C New",14.12,101.43)), ()
            )
            before=counts(db)
            first=persist_resolution_report(db,report)
            middle=counts(db)
            second=persist_resolution_report(db,report)
            self.assertEqual(first.new_places_created,1)
            self.assertEqual(second.duplicate_observations_skipped,1)
            self.assertEqual(middle[0],before[0]+1)
            self.assertEqual(counts(db),middle)

    def test_c02_review_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"db.sqlite3"; shutil.copy2(DB,db)
            p=CanonicalPlace(
                identity=PlaceIdentity(),
                canonical_name="Same",
                created_at=NOW,
                updated_at=NOW,
            )
            report=CanonicalResolutionOrchestrator().resolve_report(
                ingest(elem(99990002,"Same",province=None)), (p,)
            )
            before=counts(db)
            result=persist_resolution_report(db,report)
            self.assertEqual(result.review_skipped,1)
            self.assertEqual(counts(db),before)

    def test_c03_export_contract(self):
        with tempfile.TemporaryDirectory() as d:
            payload=export_prachinlife_json(DB,Path(d)/"x.json")
            self.assertEqual(payload["schema_version"],"prachinlife-v2-json-1")
            self.assertEqual(payload["count"],len(payload["places"]))
            if payload["places"]:
                for k in ("id","name","latitude","longitude","province","categories"):
                    self.assertIn(k,payload["places"][0])

    def test_c04_export_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"db.sqlite3"; shutil.copy2(DB,db)
            before=db.read_bytes()
            export_prachinlife_json(db,Path(d)/"x.json")
            self.assertEqual(before,db.read_bytes())

if __name__=="__main__":
    unittest.main()
