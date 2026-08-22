from __future__ import annotations

import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.discovery_resolution import (
    CanonicalResolutionOrchestrator,
)
from place_platform_v2.discovery_completion import (
    classify_review_item,
    diagnose_reviews,
)
from place_platform_v2.ingestion import (
    DiscoveryIngestionPipeline,
    DiscoveryRequest,
)
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.osm_adapter import OSMPlaceAdapterV2

NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)

def canonical(name, lat=None, lon=None):
    return CanonicalPlace(
        identity=PlaceIdentity(),
        canonical_name=name,
        location=None if lat is None else GeoPoint(lat, lon),
        created_at=NOW,
        updated_at=NOW,
    )

def elem(i, name, lat=None, lon=None):
    x = {
        "type": "node",
        "id": i,
        "tags": {
            "name": name,
            "amenity": "restaurant",
        },
    }
    if lat is not None:
        x["lat"] = lat
        x["lon"] = lon
    return x

def ingest(*elements):
    return DiscoveryIngestionPipeline().ingest(
        OSMPlaceAdapterV2(elements, observed_at=NOW),
        DiscoveryRequest("phase2b2"),
    )

class TestPhase2B2Completion(unittest.TestCase):
    def test_b2_01_name_only_review_classified_weak(self):
        p = canonical("Same")
        report = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(1, "Same")),
            (p,),
        )
        self.assertEqual(
            classify_review_item(report.items[0]),
            "weak_identity_no_geo_or_contact",
        )

    def test_b2_02_geo_review_classified_geo_name_only(self):
        p = canonical("บ้านเจสุขใจ", 14.05, 101.37)
        report = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(1, "บ้านเจ สุขใจ สาขาหลัก", 14.0502, 101.3702)),
            (p,),
        )
        if report.review_count:
            self.assertEqual(
                classify_review_item(report.items[0]),
                "geo_name_only",
            )

    def test_b2_03_diagnostics_balance(self):
        p = canonical("Same")
        report = CanonicalResolutionOrchestrator().resolve_report(
            ingest(elem(1, "Same"), elem(2, "Brand New", 15, 102)),
            (p,),
        )
        d = diagnose_reviews(report)
        self.assertEqual(
            d.total_review,
            sum(count for _, count in d.reason_counts),
        )

    def test_b2_04_samples_are_bounded(self):
        p = canonical("Same")
        report = CanonicalResolutionOrchestrator().resolve_report(
            ingest(*(elem(i, "Same") for i in range(1, 8))),
            (p,),
        )
        d = diagnose_reviews(report, sample_limit=3)
        self.assertLessEqual(len(d.sample_names), 3)

if __name__ == "__main__":
    unittest.main()
