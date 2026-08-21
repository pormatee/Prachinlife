import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from place_platform_v2.models import (
    CanonicalPlace,
    EvidenceKind,
    PlaceEvidence,
    PlaceIdentity,
    PlaceLifecycle,
)
from place_platform_v2.repository import InMemoryPlaceRepository


class TestV2PlaceModel(unittest.TestCase):
    def _source(self):
        return SourceRef(
            source_type=SourceType.OSM,
            source_name="osm_overpass",
            source_record_id="node/123",
            observed_at=datetime.now(timezone.utc),
        )

    def _place(self):
        return CanonicalPlace(
            identity=PlaceIdentity(),
            canonical_name="ร้านตัวอย่าง",
            location=GeoPoint(13.6904, 101.0779),
            province="ปราจีนบุรี",
            categories=("eat",),
            lifecycle=PlaceLifecycle.ACTIVE,
        )

    def test_11_place_has_stable_uuid_identity(self):
        place = self._place()
        self.assertTrue(place.identity.place_id)
        self.assertEqual(place.identity.place_id, place.identity.place_id)

    def test_12_place_rejects_blank_canonical_name(self):
        with self.assertRaises(ValueError):
            CanonicalPlace(identity=PlaceIdentity(), canonical_name="   ")

    def test_13_canonical_place_is_immutable(self):
        place = self._place()
        with self.assertRaises(FrozenInstanceError):
            place.canonical_name = "แก้ตรง ๆ ไม่ได้"

    def test_14_evidence_is_field_level_and_keeps_provenance(self):
        place = self._place()
        evidence = PlaceEvidence(
            place_id=place.identity.place_id,
            source=self._source(),
            kind=EvidenceKind.CATEGORY,
            field_name="categories",
            value=["vegetarian"],
            status=EvidenceStatus.SUPPORTED,
        )
        self.assertEqual(evidence.field_name, "categories")
        self.assertEqual(evidence.source.source_record_id, "node/123")

    def test_15_evidence_does_not_mutate_canonical_place(self):
        place = self._place()
        original_categories = place.categories
        PlaceEvidence(
            place_id=place.identity.place_id,
            source=self._source(),
            kind=EvidenceKind.CATEGORY,
            field_name="categories",
            value=["vegetarian"],
        )
        self.assertEqual(place.categories, original_categories)

    def test_16_repository_rejects_orphan_evidence(self):
        repo = InMemoryPlaceRepository()
        evidence = PlaceEvidence(
            place_id=PlaceIdentity().place_id,
            source=self._source(),
            kind=EvidenceKind.EXISTENCE,
            field_name="existence",
            value=True,
        )
        with self.assertRaises(KeyError):
            repo.add_evidence(evidence)

    def test_17_repository_persists_place_and_multiple_evidence(self):
        repo = InMemoryPlaceRepository()
        place = self._place()
        repo.save_place(place)

        first = PlaceEvidence(
            place_id=place.identity.place_id,
            source=self._source(),
            kind=EvidenceKind.EXISTENCE,
            field_name="existence",
            value=True,
        )
        second = PlaceEvidence(
            place_id=place.identity.place_id,
            source=SourceRef(
                source_type=SourceType.MANUAL,
                source_name="manual_seed",
            ),
            kind=EvidenceKind.NAME,
            field_name="canonical_name",
            value="ร้านตัวอย่าง",
        )
        repo.add_evidence(first)
        repo.add_evidence(second)

        loaded = repo.get_place(place.identity.place_id)
        self.assertEqual(loaded, place)
        self.assertEqual(len(repo.list_evidence(place.identity.place_id)), 2)

    def test_18_duplicate_evidence_id_is_rejected(self):
        repo = InMemoryPlaceRepository()
        place = self._place()
        repo.save_place(place)
        evidence = PlaceEvidence(
            place_id=place.identity.place_id,
            source=self._source(),
            kind=EvidenceKind.EXISTENCE,
            field_name="existence",
            value=True,
        )
        repo.add_evidence(evidence)
        with self.assertRaises(ValueError):
            repo.add_evidence(evidence)

    def test_19_repository_contract_is_database_agnostic(self):
        import inspect
        import place_platform_v2.repository as repository

        source = inspect.getsource(repository)
        forbidden = ("sqlite3", "psycopg", "sqlalchemy", "postgresql://")
        self.assertFalse(any(token in source for token in forbidden))

    def test_20_manual_source_uses_same_evidence_model_as_automated_sources(self):
        place = self._place()
        evidence = PlaceEvidence(
            place_id=place.identity.place_id,
            source=SourceRef(
                source_type=SourceType.MANUAL,
                source_name="curated_manual_entry",
            ),
            kind=EvidenceKind.LOCATION,
            field_name="location",
            value={"latitude": 13.69, "longitude": 101.08},
        )
        self.assertEqual(evidence.source.source_type, SourceType.MANUAL)
        self.assertEqual(evidence.status, EvidenceStatus.CANDIDATE)


if __name__ == "__main__":
    unittest.main()
