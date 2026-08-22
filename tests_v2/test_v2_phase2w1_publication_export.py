from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from place_platform_v2.models import CanonicalPlace, EvidenceKind, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from place_platform_v2.publication_export import (
    build_staged_payload,
    evaluate_publication_database,
    write_staged_export,
)
from place_platform_v2.sqlite_store import SQLitePlaceRepository

NOW = datetime(2026, 8, 22, tzinfo=timezone.utc)


def evidence(place_id, field, value, source_name, record_id):
    return PlaceEvidence(
        place_id=place_id,
        source=SourceRef(SourceType.OTHER, source_name, source_record_id=record_id, observed_at=NOW),
        kind=EvidenceKind.OTHER,
        field_name=field,
        value=value,
        status=EvidenceStatus.CANDIDATE,
        observed_at=NOW,
    )


def seed_verified_place(db):
    repo = SQLitePlaceRepository(db)
    place = CanonicalPlace(
        identity=PlaceIdentity(), canonical_name="ร้านทดสอบ",
        location=GeoPoint(14.05, 101.37), province="ปราจีนบุรี",
        categories=("eat",), lifecycle=PlaceLifecycle.ACTIVE,
        created_at=NOW, updated_at=NOW,
    )
    repo.save_place(place)
    for field in ("canonical_name", "location", "province", "categories", "lifecycle"):
        value = getattr(place, field)
        repo.add_evidence(evidence(place.identity.place_id, field, value, "source-a", f"a-{field}"))
        repo.add_evidence(evidence(place.identity.place_id, field, value, "source-b", f"b-{field}"))
    repo.close()


class TestPhase2W1PublicationExport(unittest.TestCase):
    def test_w101_verified_active_place_is_only_eligible_source(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td)/"x.sqlite3"; seed_verified_place(db)
            report, decisions = evaluate_publication_database(db)
            self.assertEqual(report.eligible_count, 1)
            self.assertEqual(build_staged_payload(decisions, province="ปราจีนบุรี")["count"], 1)

    def test_w102_unknown_lifecycle_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td)/"x.sqlite3"; repo=SQLitePlaceRepository(db)
            p=CanonicalPlace(identity=PlaceIdentity(), canonical_name="X", location=GeoPoint(14,101), province="ปราจีนบุรี", categories=("eat",), lifecycle=PlaceLifecycle.UNKNOWN, created_at=NOW, updated_at=NOW)
            repo.save_place(p); repo.close()
            report, decisions=evaluate_publication_database(db)
            self.assertEqual(report.eligible_count,0); self.assertEqual(build_staged_payload(decisions,province="ปราจีนบุรี")["count"],0)

    def test_w103_empty_payload_is_not_written(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"staging"
            with self.assertRaisesRegex(ValueError,"fail-closed"):
                write_staged_export({"count":0,"places":[]},output_path=root/"x.json",staging_root=root)
            self.assertFalse((root/"x.json").exists())

    def test_w104_output_must_stay_inside_staging(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"staging"
            with self.assertRaisesRegex(ValueError,"only inside"):
                write_staged_export({"count":1,"places":[{}]},output_path=Path(td)/"prod.json",staging_root=root)

    def test_w105_real_export_contains_publication_metadata_not_internal_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"x.sqlite3"; seed_verified_place(db)
            _, decisions=evaluate_publication_database(db)
            payload=build_staged_payload(decisions,province="ปราจีนบุรี",published_at=NOW)
            item=payload["places"][0]
            self.assertEqual(item["source"],"place_platform_v2_published")
            self.assertIn("publication_policy_version",item)
            self.assertNotIn("evidence",item); self.assertNotIn("revision",item)

    def test_w106_evaluation_is_read_only_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"x.sqlite3"; seed_verified_place(db); before=db.read_bytes()
            evaluate_publication_database(db)
            self.assertEqual(db.read_bytes(),before)

    def test_w107_report_never_claims_store_or_web_switch(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"x.sqlite3"; seed_verified_place(db)
            report,_=evaluate_publication_database(db)
            self.assertFalse(report.publication_store_written); self.assertFalse(report.user_web_switched)


if __name__ == "__main__": unittest.main()
