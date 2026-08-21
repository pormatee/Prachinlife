from datetime import datetime, timezone
import unittest

from place_platform_v2.contracts import EvidenceStatus, SourceRef, SourceType
from place_platform_v2.models import EvidenceKind, PlaceEvidence, PlaceIdentity
from place_platform_v2.verification import (
    EvidenceVerificationEngine,
    VerificationOutcome,
    VerificationPolicy,
    aggregate_field_evidence,
    verify_field,
)


NOW = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)


def evidence(place_id, value, source_type, source_name, *, record_id=None, status=EvidenceStatus.CANDIDATE):
    return PlaceEvidence(
        place_id=place_id,
        source=SourceRef(
            source_type=source_type,
            source_name=source_name,
            source_record_id=record_id,
            observed_at=NOW,
        ),
        kind=EvidenceKind.NAME,
        field_name="canonical_name",
        value=value,
        status=status,
        observed_at=NOW,
    )


class TestV2Verification(unittest.TestCase):
    def setUp(self):
        self.place_id = PlaceIdentity().place_id

    def test_01_no_evidence_is_insufficient(self):
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=())
        self.assertEqual(result.outcome, VerificationOutcome.INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.may_adopt)
        self.assertIsNone(result.selected_value)

    def test_02_single_source_is_supported_not_verified(self):
        result = verify_field(
            place_id=self.place_id,
            field_name="canonical_name",
            evidence=(evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),),
        )
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)
        self.assertEqual(result.selected_value, "ร้าน A")
        self.assertTrue(result.may_adopt)

    def test_03_two_independent_sources_verify_same_value(self):
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),
            evidence(self.place_id, "ร้าน A", SourceType.WEB, "web-search"),
        )
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=items)
        self.assertEqual(result.outcome, VerificationOutcome.VERIFIED)
        self.assertEqual(result.supports[0].source_count, 2)
        self.assertEqual(result.evidence_status, EvidenceStatus.VERIFIED)

    def test_04_repeated_same_source_record_does_not_inflate_quorum(self):
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm", record_id="node/1"),
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm", record_id="node/1"),
        )
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=items)
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)
        self.assertEqual(result.supports[0].source_count, 1)
        self.assertEqual(result.supports[0].evidence_count, 2)

    def test_05_competing_active_values_are_conflicting(self):
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),
            evidence(self.place_id, "ร้าน B", SourceType.WEB, "web-search"),
        )
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=items)
        self.assertEqual(result.outcome, VerificationOutcome.CONFLICTING)
        self.assertFalse(result.may_adopt)
        self.assertIsNone(result.selected_value)

    def test_06_rejected_evidence_does_not_create_conflict(self):
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),
            evidence(self.place_id, "ร้าน B", SourceType.WEB, "web-search", status=EvidenceStatus.REJECTED),
        )
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=items)
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)
        self.assertEqual(result.selected_value, "ร้าน A")

    def test_07_stale_evidence_does_not_verify_current_value(self):
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),
            evidence(self.place_id, "ร้าน A", SourceType.WEB, "web-search", status=EvidenceStatus.STALE),
        )
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=items)
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)

    def test_08_other_place_evidence_is_ignored(self):
        other = PlaceIdentity().place_id
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),
            evidence(other, "ร้าน A", SourceType.WEB, "web-search"),
        )
        result = verify_field(place_id=self.place_id, field_name="canonical_name", evidence=items)
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)
        self.assertEqual(result.supports[0].source_count, 1)

    def test_09_aggregation_handles_category_sequences_deterministically(self):
        items = (
            PlaceEvidence(
                place_id=self.place_id,
                source=SourceRef(SourceType.OSM, "osm", observed_at=NOW),
                kind=EvidenceKind.CATEGORY,
                field_name="categories",
                value=("eat", "vegetarian"),
                observed_at=NOW,
            ),
            PlaceEvidence(
                place_id=self.place_id,
                source=SourceRef(SourceType.WEB, "web", observed_at=NOW),
                kind=EvidenceKind.CATEGORY,
                field_name="categories",
                value=("vegetarian", "eat"),
                observed_at=NOW,
            ),
        )
        supports = aggregate_field_evidence(items, "categories")
        self.assertEqual(len(supports), 1)
        self.assertEqual(supports[0].source_count, 2)

    def test_10_policy_is_explicit_and_versionable_boundary(self):
        policy = VerificationPolicy(verified_independent_sources=3, supported_sources=1)
        items = (
            evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),
            evidence(self.place_id, "ร้าน A", SourceType.WEB, "web"),
        )
        result = verify_field(
            place_id=self.place_id,
            field_name="canonical_name",
            evidence=items,
            policy=policy,
        )
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)

    def test_11_engine_is_side_effect_free(self):
        item = evidence(self.place_id, "ร้าน A", SourceType.MANUAL, "manual")
        before = item.status
        result = EvidenceVerificationEngine().verify_field(
            place_id=self.place_id,
            field_name="canonical_name",
            evidence=(item,),
        )
        self.assertEqual(result.outcome, VerificationOutcome.SUPPORTED)
        self.assertEqual(item.status, before)

    def test_12_verification_does_not_publish(self):
        result = verify_field(
            place_id=self.place_id,
            field_name="canonical_name",
            evidence=(evidence(self.place_id, "ร้าน A", SourceType.OSM, "osm"),),
        )
        self.assertFalse(hasattr(result, "publishable"))
        self.assertFalse(hasattr(result, "publish"))


if __name__ == "__main__":
    unittest.main()
