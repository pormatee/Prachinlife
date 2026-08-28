from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.decision_quality_engine_v1 import evaluate_decision_quality
from place_platform_v2.master_super_brain_v1 import DecisionConstraint, DecisionRequest
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.real_candidate_mapping_v1 import (
    PublishedDecisionQuery,
    ReadOnlyPublishedSQLiteSource,
    published_place_to_decision_candidate,
)


def view(pid="p1", categories=("vegetarian",), lat=14.05, lon=101.37):
    return PublishedPlaceView(
        place_id=pid,
        name=f"Place {pid}",
        location=GeoPoint(lat, lon),
        province="ปราจีนบุรี",
        categories=categories,
        lifecycle=PlaceLifecycle.ACTIVE,
        address_text="test",
        publication_policy_version="policy-test",
        published_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
    )


class RealCandidateMappingV1Tests(unittest.TestCase):
    def test_published_core_fields_map_as_publication_evidence(self):
        c = published_place_to_decision_candidate(view())
        self.assertEqual(c.candidate_id, "p1")
        self.assertEqual(c.attributes["province"], "ปราจีนบุรี")
        fields = {e.field: e for e in c.evidence}
        for f in ("name","province","categories","lifecycle","location"):
            self.assertEqual(fields[f].status, "verified")
            self.assertTrue(fields[f].source_ref.startswith("published:policy-test:"))

    def test_vegetarian_is_supported_inference_not_verified_fact(self):
        c = published_place_to_decision_candidate(view(categories=("อาหารเจ","restaurant")))
        item = next(e for e in c.evidence if e.field == "vegetarian")
        self.assertTrue(c.attributes["vegetarian"])
        self.assertEqual(item.status, "supported")
        self.assertLess(item.confidence, 1.0)

    def test_absence_of_vegetarian_category_does_not_mean_false(self):
        c = published_place_to_decision_candidate(view(categories=("restaurant",)))
        self.assertNotIn("vegetarian", c.attributes)
        self.assertFalse(any(e.field == "vegetarian" for e in c.evidence))

    def test_distance_is_derived_supported_evidence(self):
        c = published_place_to_decision_candidate(
            view(), origin=GeoPoint(14.05, 101.37), distance_scale_km=10
        )
        self.assertAlmostEqual(c.attributes["distance_km"], 0.0, places=6)
        e = next(e for e in c.evidence if e.field == "distance_norm")
        self.assertEqual(e.status, "supported")

    def test_dynamic_facts_are_not_fabricated(self):
        c = published_place_to_decision_candidate(view())
        for f in ("open_now","in_stock","price_norm","available_now","weather_fit"):
            self.assertNotIn(f, c.attributes)
            self.assertFalse(any(e.field == f for e in c.evidence))

    def test_dqe_fails_closed_when_open_now_is_required_but_missing(self):
        q = DecisionRequest(
            "real-map-1","vegetarian dinner now",category="vegetarian",
            constraints=(
                DecisionConstraint("vegetarian","eq",True,"hard",10),
                DecisionConstraint("open_now","eq",True,"soft",5),
            ),
        )
        c = published_place_to_decision_candidate(
            view(), origin=GeoPoint(14.05,101.37)
        )
        r = evaluate_decision_quality(q,(c,))
        self.assertEqual(r.status, "insufficient_data")
        self.assertTrue(r.decision_boundary.human_decides)

    def test_read_only_sqlite_source_reads_published_places(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td)/"x.sqlite3"
            con=sqlite3.connect(db)
            con.execute("""CREATE TABLE published_places(
              place_id TEXT PRIMARY KEY,name TEXT,latitude REAL,longitude REAL,
              province TEXT,categories_json TEXT,lifecycle TEXT,address_text TEXT,
              phone TEXT,website TEXT,publication_policy_version TEXT,published_at TEXT)""")
            con.execute("INSERT INTO published_places VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(
                "p1","ร้านเจ",14.05,101.37,"ปราจีนบุรี",json.dumps(["vegetarian"]),
                "active",None,None,None,"policy-test","2026-08-28T00:00:00+00:00"))
            con.commit(); con.close()
            src=ReadOnlyPublishedSQLiteSource(db)
            self.assertEqual(src.count(),1)
            cs=src.decision_candidates(PublishedDecisionQuery(
                province="ปราจีนบุรี",origin=GeoPoint(14.05,101.37),radius_km=5))
            self.assertEqual([c.candidate_id for c in cs],["p1"])

    def test_query_cannot_request_radius_without_origin(self):
        with self.assertRaises(ValueError):
            PublishedDecisionQuery(radius_km=5)

if __name__ == "__main__":
    unittest.main()
