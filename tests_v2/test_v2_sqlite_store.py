from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.adoption import PlaceRevision
from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from place_platform_v2.models import CanonicalPlace, EvidenceKind, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from place_platform_v2.persistence import NearbyPlaceQuery
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.read_model import PublishedNearbyQuery, PublishedTextQuery
from place_platform_v2.sqlite_store import (
    SQLITE_SCHEMA_VERSION,
    SQLitePlaceRepository,
    SQLitePublishedPlaceRepository,
)

NOW = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 21, 1, 0, tzinfo=timezone.utc)


def place(name="ร้าน A", lat=14.05, lon=101.37, categories=("eat",), lifecycle=PlaceLifecycle.ACTIVE):
    return CanonicalPlace(
        identity=PlaceIdentity(), canonical_name=name,
        location=GeoPoint(lat, lon), province="ปราจีนบุรี", categories=categories,
        lifecycle=lifecycle, created_at=NOW, updated_at=NOW,
    )


def view(source: CanonicalPlace) -> PublishedPlaceView:
    return PublishedPlaceView(
        place_id=source.identity.place_id, name=source.canonical_name,
        location=source.location, province=source.province, categories=source.categories,
        lifecycle=PlaceLifecycle.ACTIVE, publication_policy_version="1.0-packet8",
        published_at=NOW,
    )


class TestV2SQLiteStore(unittest.TestCase):
    def test_01_sqlite_internal_place_round_trip(self):
        repo = SQLitePlaceRepository()
        item = place()
        repo.save_place(item)
        self.assertEqual(repo.get_place(item.identity.place_id), item)
        repo.close()

    def test_02_file_database_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "places.sqlite3"
            item = place()
            with SQLitePlaceRepository(path) as repo:
                repo.save_place(item)
            with SQLitePlaceRepository(path) as repo:
                self.assertEqual(repo.get_place(item.identity.place_id), item)

    def test_03_evidence_round_trip_preserves_provenance_and_typed_value(self):
        repo = SQLitePlaceRepository()
        item = place()
        repo.save_place(item)
        evidence = PlaceEvidence(
            place_id=item.identity.place_id,
            source=SourceRef(SourceType.OSM, "OpenStreetMap", "node/1", observed_at=NOW),
            kind=EvidenceKind.LOCATION, field_name="location",
            value=GeoPoint(14.051, 101.371), status=EvidenceStatus.VERIFIED,
            observed_at=NOW, metadata={"quality": "test"},
        )
        repo.add_evidence(evidence)
        self.assertEqual(repo.list_evidence(item.identity.place_id), (evidence,))
        repo.close()

    def test_04_evidence_requires_existing_place(self):
        repo = SQLitePlaceRepository()
        evidence = PlaceEvidence(
            place_id=PlaceIdentity().place_id,
            source=SourceRef(SourceType.MANUAL, "manual", observed_at=NOW),
            kind=EvidenceKind.NAME, field_name="canonical_name", value="X", observed_at=NOW,
        )
        with self.assertRaises(KeyError):
            repo.add_evidence(evidence)
        repo.close()

    def test_05_duplicate_evidence_is_rejected(self):
        repo = SQLitePlaceRepository()
        item = place(); repo.save_place(item)
        evidence = PlaceEvidence(
            place_id=item.identity.place_id,
            source=SourceRef(SourceType.WEB, "web", observed_at=NOW),
            kind=EvidenceKind.NAME, field_name="canonical_name", value="A", observed_at=NOW,
        )
        repo.add_evidence(evidence)
        with self.assertRaises(ValueError):
            repo.add_evidence(evidence)
        repo.close()

    def test_06_adoption_commit_persists_place_and_revision(self):
        repo = SQLitePlaceRepository()
        item = place(); repo.save_place(item)
        updated = replace(item, canonical_name="ร้านใหม่", updated_at=LATER)
        revision = PlaceRevision(
            revision_id=PlaceIdentity().place_id, place_id=item.identity.place_id,
            changed_fields=("canonical_name",), before_values={"canonical_name": "ร้าน A"},
            after_values={"canonical_name": "ร้านใหม่"}, reason="verified evidence",
            evidence_ids=(), policy_version="1.0-packet7", created_at=LATER,
        )
        repo.commit_adoption(updated, revision)
        self.assertEqual(repo.get_place(item.identity.place_id).canonical_name, "ร้านใหม่")
        self.assertEqual(repo.list_revisions(item.identity.place_id), (revision,))
        repo.close()

    def test_07_duplicate_revision_rolls_back_canonical_update_atomically(self):
        repo = SQLitePlaceRepository()
        item = place(); repo.save_place(item)
        revision_id = PlaceIdentity().place_id
        first = replace(item, canonical_name="ชื่อหนึ่ง", updated_at=LATER)
        revision = PlaceRevision(
            revision_id=revision_id, place_id=item.identity.place_id,
            changed_fields=("canonical_name",), before_values={"canonical_name": "ร้าน A"},
            after_values={"canonical_name": "ชื่อหนึ่ง"}, reason="first", evidence_ids=(),
            policy_version="1.0-packet7", created_at=LATER,
        )
        repo.commit_adoption(first, revision)
        second = replace(first, canonical_name="ต้องไม่ค้าง")
        with self.assertRaises(ValueError):
            repo.commit_adoption(second, revision)
        self.assertEqual(repo.get_place(item.identity.place_id).canonical_name, "ชื่อหนึ่ง")
        repo.close()

    def test_08_sqlite_internal_near_me_matches_contract(self):
        repo = SQLitePlaceRepository()
        near = place("ใกล้", 14.0505, 101.3705)
        far = place("ไกล", 14.08, 101.40)
        repo.save_place(far); repo.save_place(near)
        results = repo.search_nearby(NearbyPlaceQuery(GeoPoint(14.05, 101.37), 20))
        self.assertEqual(tuple(r.place_id for r in results), (near.identity.place_id, far.identity.place_id))
        repo.close()

    def test_09_sqlite_near_me_respects_category_and_lifecycle(self):
        repo = SQLitePlaceRepository()
        veg = place("เจ", 14.0505, 101.3705, ("vegetarian",))
        closed = place("ปิด", 14.0506, 101.3706, ("vegetarian",), PlaceLifecycle.CLOSED)
        repo.save_place(veg); repo.save_place(closed)
        results = repo.search_nearby(NearbyPlaceQuery(GeoPoint(14.05, 101.37), 5, categories=("vegetarian",)))
        self.assertEqual(tuple(r.place_id for r in results), (veg.identity.place_id,))
        repo.close()

    def test_10_published_view_round_trip_and_upsert(self):
        repo = SQLitePublishedPlaceRepository()
        item = place(); original = view(item)
        repo.upsert_published(original)
        updated = replace(original, name="ชื่อใหม่", published_at=LATER)
        repo.upsert_published(updated)
        self.assertEqual(repo.get_published(item.identity.place_id), updated)
        repo.close()

    def test_11_published_store_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "published.sqlite3"
            item = view(place())
            with SQLitePublishedPlaceRepository(path) as repo:
                repo.upsert_published(item)
            with SQLitePublishedPlaceRepository(path) as repo:
                self.assertEqual(repo.get_published(item.place_id), item)

    def test_12_published_search_nearby_filters(self):
        repo = SQLitePublishedPlaceRepository()
        veg = view(place("ร้านเจ", 14.0505, 101.3705, ("vegetarian",)))
        eat = view(place("ร้านทั่วไป", 14.0506, 101.3706, ("eat",)))
        repo.upsert_published(veg); repo.upsert_published(eat)
        results = repo.search_nearby(PublishedNearbyQuery(GeoPoint(14.05, 101.37), 5, categories=("vegetarian",), province="ปราจีนบุรี"))
        self.assertEqual(tuple(r.place.place_id for r in results), (veg.place_id,))
        repo.close()

    def test_13_published_text_search_and_remove(self):
        repo = SQLitePublishedPlaceRepository()
        item = view(place("Green   Garden", 14.05, 101.37, ("vegetarian",)))
        repo.upsert_published(item)
        self.assertEqual(len(repo.search_text(PublishedTextQuery(text="green garden"))), 1)
        repo.remove_published(item.place_id)
        self.assertEqual(repo.search_text(PublishedTextQuery()), ())
        repo.close()

    def test_14_internal_and_published_stores_are_separate_boundaries(self):
        internal = SQLitePlaceRepository()
        published = SQLitePublishedPlaceRepository()
        item = place(); internal.save_place(item)
        self.assertIsNone(published.get_published(item.identity.place_id))
        published.upsert_published(view(item))
        self.assertEqual(internal.get_place(item.identity.place_id), item)
        internal.close(); published.close()

    def test_15_sqlite_reference_store_has_no_external_database_dependency(self):
        import inspect
        import place_platform_v2.sqlite_store as module
        source = inspect.getsource(module)
        self.assertIn("import sqlite3", source)
        self.assertNotIn("import psycopg", source)
        self.assertNotIn("import sqlalchemy", source)
        self.assertTrue(SQLITE_SCHEMA_VERSION.endswith("packet10"))


if __name__ == "__main__":
    unittest.main()
