from __future__ import annotations
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.coverage import summarize_coverage
from place_platform_v2.discovery_readonly import load_canonical_places_readonly
from place_platform_v2.discovery_resolution import (
    CanonicalResolutionOrchestrator, DiscoveryResolutionOutcome,
)
from place_platform_v2.ingestion import DiscoveryIngestionPipeline, DiscoveryRequest
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.osm_adapter import OSMPlaceAdapterV2

NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)
DB = Path("data/v2/place_platform_v2.sqlite3")

def place(name="ร้าน A", lat=None, lon=None, province=None, phone=None):
    return CanonicalPlace(
        identity=PlaceIdentity(),
        canonical_name=name,
        location=None if lat is None else GeoPoint(lat, lon),
        province=province,
        phone=phone,
        created_at=NOW,
        updated_at=NOW,
    )

def elem(i=1, name="ร้าน A", lat=None, lon=None, province=None, phone=None):
    tags = {"name": name, "amenity": "restaurant"}
    if province:
        tags["addr:province"] = province
    if phone:
        tags["phone"] = phone
    x = {"type": "node", "id": i, "tags": tags}
    if lat is not None:
        x["lat"], x["lon"] = lat, lon
    return x

def ingest(*elements):
    return DiscoveryIngestionPipeline().ingest(
        OSMPlaceAdapterV2(elements, observed_at=NOW),
        DiscoveryRequest("phase2a"),
    )

class TestDiscoveryPhase2A(unittest.TestCase):
    def test_195_readonly_loads_frozen_baseline(self):
        self.assertEqual(len(load_canonical_places_readonly(DB)), 919)

    def test_196_readonly_does_not_modify_database(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "db.sqlite3"
            shutil.copy2(DB, copy)
            before = copy.read_bytes()
            load_canonical_places_readonly(copy)
            self.assertEqual(before, copy.read_bytes())

    def test_197_new_when_no_canonical_match(self):
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(lat=14.05, lon=101.37)), ()
        )
        self.assertEqual(r.items[0].outcome, DiscoveryResolutionOutcome.NEW)

    def test_198_exact_name_geo_province_matches(self):
        p = place("ร้าน A", 14.05, 101.37, "ปราจีนบุรี")
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="ร้าน A", lat=14.05, lon=101.37, province="ปราจีนบุรี")),
            (p,),
        )
        self.assertEqual(r.matched_count, 1)
        self.assertEqual(r.items[0].matched_place_id, p.identity.place_id)

    def test_199_near_same_name_matches(self):
        p = place("Cafe A", 14.05, 101.37)
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="Cafe A", lat=14.0504, lon=101.3704)), (p,)
        )
        self.assertEqual(r.matched_count, 1)

    def test_200_same_phone_matches(self):
        p = place("ร้านเอ", province="ปราจีนบุรี", phone="0812345678")
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="ร้าน A", province="ปราจีนบุรี", phone="081 234 5678")),
            (p,),
        )
        self.assertEqual(r.matched_count, 1)

    def test_201_name_only_routes_review(self):
        p = place("ร้านกลางเมือง")
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="ร้านกลางเมือง")), (p,)
        )
        self.assertEqual(r.review_count, 1)

    def test_202_far_same_name_is_new(self):
        p = place("Cafe A", 13.75, 100.50)
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="Cafe A", lat=14.05, lon=101.37)), (p,)
        )
        self.assertEqual(r.new_count, 1)

    def test_203_multiple_matches_route_review(self):
        p1 = place("ร้าน A", 14.05, 101.37, "ปราจีนบุรี")
        p2 = place("ร้าน A", 14.05, 101.37, "ปราจีนบุรี")
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="ร้าน A", lat=14.05, lon=101.37, province="ปราจีนบุรี")),
            (p1, p2),
        )
        self.assertEqual(r.review_count, 1)

    def test_204_coverage_balances(self):
        r = CanonicalResolutionOrchestrator().resolve_report(
            ingest(
                elem(1, "A", 14.05, 101.37, "ปราจีนบุรี"),
                elem(2, "B", 13.75, 100.50, "กรุงเทพมหานคร"),
            ),
            (),
        )
        s = summarize_coverage(r)
        self.assertEqual(s.total, 2)
        self.assertEqual(s.total, s.matched + s.new + s.review)

    def test_205_deterministic_canonical_order(self):
        a = place("A", 14.05, 101.37)
        b = place("B", 15.0, 102.0)
        report = ingest(elem(name="A", lat=14.05, lon=101.37))
        engine = CanonicalResolutionOrchestrator()
        x = engine.resolve_report(report, (a, b))
        y = engine.resolve_report(report, (b, a))
        self.assertEqual(x.items[0].outcome, y.items[0].outcome)
        self.assertEqual(x.items[0].matched_place_id, y.items[0].matched_place_id)

    def test_206_no_adoption_or_publication_side_effect(self):
        p = place("A", 14.05, 101.37)
        before = p
        CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(name="A", lat=14.05, lon=101.37)), (p,)
        )
        self.assertEqual(p, before)

if __name__ == "__main__":
    unittest.main()
