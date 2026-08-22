from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from place_platform_v2.models import CanonicalPlace, EvidenceKind, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from place_platform_v2.sqlite_store import SQLitePlaceRepository
from place_platform_v2.verification_source_acquisition import SourceObservation, evaluate_source_observation

NOW = datetime(2026, 8, 22, tzinfo=timezone.utc)


def seed(db):
    repo = SQLitePlaceRepository(db)
    place = CanonicalPlace(
        identity=PlaceIdentity(),
        canonical_name="คาลเท็กซ์",
        location=GeoPoint(13.7709337, 102.0231286),
        province="ปราจีนบุรี",
        categories=("fuel",),
        lifecycle=PlaceLifecycle.UNKNOWN,
        created_at=NOW,
        updated_at=NOW,
    )
    repo.save_place(place)
    osm = SourceRef(
        SourceType.OSM,
        "OpenStreetMap",
        source_record_id="node-2174718705",
        source_url="https://www.openstreetmap.org/node/2174718705",
        observed_at=NOW,
    )
    repo.add_evidence(PlaceEvidence(
        place_id=place.identity.place_id,
        source=osm,
        kind=EvidenceKind.LOCATION,
        field_name="location",
        value=place.location,
        status=EvidenceStatus.CANDIDATE,
        observed_at=NOW,
    ))
    repo.close()
    return place


def obs(*, province="ปราจีนบุรี", lat=13.7709337, lon=102.0231286, name="Caltex", active=True, source=None):
    source = source or SourceRef(
        SourceType.OFFICIAL,
        "Independent Official",
        source_record_id="station-99",
        source_url="https://official.example/station/99",
        observed_at=NOW,
    )
    return SourceObservation(
        source=source,
        place_name=name,
        province=province,
        location=None if lat is None else GeoPoint(lat, lon),
        lifecycle=PlaceLifecycle.ACTIVE if active else None,
    )


class TestPhase2W4VerificationSourceAcquisition(unittest.TestCase):
    def test_w401_exact_independent_source_is_verification_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs())
            self.assertEqual(r.result, "verification_candidate")
            self.assertTrue(r.can_create_verification_bundle)

    def test_w402_exact_geo_with_other_province_is_scope_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs(province="สระแก้ว"))
            self.assertEqual(r.result, "scope_conflict")
            self.assertEqual(r.required_action, "canonical_correction_review")

    def test_w403_missing_location_is_insufficient_anchor(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs(lat=None, lon=None))
            self.assertEqual(r.result, "insufficient_anchor")

    def test_w404_far_source_is_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs(lat=13.90, lon=102.20))
            self.assertEqual(r.result, "unresolved_match")

    def test_w405_near_conflicting_name_is_identity_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs(name="PTT"))
            self.assertEqual(r.result, "identity_conflict")

    def test_w406_same_osm_lineage_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            same = SourceRef(
                SourceType.OTHER,
                "OSM mirror",
                source_record_id="copy-osm-node-2174718705",
                source_url="https://mirror.example/osm/node/2174718705",
                observed_at=NOW,
            )
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs(source=same))
            self.assertEqual(r.result, "blocked_same_lineage")

    def test_w407_identity_match_without_active_lifecycle_is_not_bundle_ready(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"; p = seed(db)
            r = evaluate_source_observation(db, place_id=p.identity.place_id, observation=obs(active=False))
            self.assertEqual(r.result, "identity_match_no_lifecycle")
            self.assertFalse(r.can_create_verification_bundle)


if __name__ == "__main__":
    unittest.main()
