import re
import shutil
import sqlite3
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.publication_readiness import _load_places_and_evidence
from place_platform_v2.staged_milestone import (
    acquire_osm_queue,
    commit_current_observations,
    eligible_place_ids,
    osm_ref,
    select_identity_anchor_queue,
)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/v2/place_platform_v2.sqlite3"


class TestIdentityAnchorRollout(unittest.TestCase):
    def test_queue_excludes_existing_eligible(self):
        queue = select_identity_anchor_queue(DB)
        eligible, _ = eligible_place_ids(DB)
        self.assertTrue({x["place_id"] for x in queue}.isdisjoint(set(eligible)))

    def test_osm_identity_anchor_is_unique(self):
        queue = select_identity_anchor_queue(DB)
        refs = [(x["osm_type"], x["osm_id"]) for x in queue]
        self.assertEqual(len(refs), len(set(refs)))

    def test_queue_is_deterministic(self):
        self.assertEqual(select_identity_anchor_queue(DB), select_identity_anchor_queue(DB))

    def test_duplicate_names_have_distinct_osm_identity_anchors(self):
        places, by = _load_places_and_evidence(DB, "ปราจีนบุรี")
        counts = Counter(p.canonical_name.strip().casefold() for p in places)
        refs = []
        duplicate_places = 0
        for place in places:
            if counts[place.canonical_name.strip().casefold()] <= 1:
                continue
            ref = osm_ref(by.get(place.identity.place_id, ()))
            if ref:
                duplicate_places += 1
                refs.append(ref)
        self.assertGreater(duplicate_places, 0)
        self.assertEqual(len(refs), len(set(refs)))

    def test_way_acquisition_uses_way_endpoint_and_preserves_way_provenance(self):
        seen = []
        queue = [{
            "place_id": "x",
            "canonical_name": "Area",
            "province": "ปราจีนบุรี",
            "latitude": 14.0,
            "longitude": 101.0,
            "osm_type": "way",
            "osm_id": "123",
        }]
        payload = b'<osm><way id="123"><tag k="name" v="Area"/></way></osm>'
        obs = acquire_osm_queue(
            queue,
            fetcher=lambda url: seen.append(url) or payload,
            observed_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
        )
        self.assertEqual(obs[0]["status"], "current_listing")
        self.assertTrue(seen[0].endswith("/way/123/full"))
        self.assertEqual(obs[0]["source_url"], "https://www.openstreetmap.org/way/123")

    def test_commit_uses_object_type_in_source_record_id(self):
        places, by = _load_places_and_evidence(DB, "ปราจีนบุรี")
        chosen = None
        for place in places:
            ref = osm_ref(by.get(place.identity.place_id, ()))
            if ref and ref[0] == "way" and place.location:
                chosen = (place, ref)
                break
        self.assertIsNotNone(chosen)
        place, ref = chosen
        observation = {
            "place_id": place.identity.place_id,
            "canonical_name": place.canonical_name,
            "province": place.province,
            "latitude": place.location.latitude,
            "longitude": place.location.longitude,
            "osm_type": "way",
            "osm_id": ref[1],
            "status": "current_listing",
            "source_url": f"https://www.openstreetmap.org/way/{ref[1]}",
            "observed_at": "2026-08-22T12:34:56+00:00",
        }
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "copy.sqlite3"
            shutil.copy2(DB, db)
            committed = commit_current_observations(db, [observation])
            self.assertEqual(len(committed), 1)
            con = sqlite3.connect(db)
            try:
                row = con.execute(
                    "select source_record_id from place_evidence where evidence_id=?",
                    (committed[0]["evidence_id"],),
                ).fetchone()
            finally:
                con.close()
            self.assertEqual(row[0], f"osm-way-{ref[1]}")


if __name__ == "__main__":
    unittest.main()
