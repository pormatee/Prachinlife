from __future__ import annotations

import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint, SourcePlaceCandidate, SourceRef, SourceType
from place_platform_v2.entity_resolution import (
    EntityResolutionEngine,
    ResolutionOutcome,
    ResolutionPolicy,
    ResolutionSignal,
)
from place_platform_v2.ingestion import IngestionObservation, build_claims, normalize_candidate


NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)


def observation(
    *,
    name="ร้าน A",
    source_type=SourceType.OSM,
    source_name="OSM",
    record_id=None,
    lat=None,
    lon=None,
    province=None,
    phone=None,
    website=None,
):
    location = None if lat is None else GeoPoint(lat, lon)
    candidate = normalize_candidate(
        SourcePlaceCandidate(
            source=SourceRef(
                source_type=source_type,
                source_name=source_name,
                source_record_id=record_id,
                observed_at=NOW,
            ),
            name=name,
            location=location,
            province=province,
            phone=phone,
            website=website,
        )
    )
    return IngestionObservation(candidate=candidate, claims=build_claims(candidate))


class TestV2EntityResolution(unittest.TestCase):
    def test_42_same_source_record_is_same_entity(self):
        left = observation(record_id="123", lat=14.05, lon=101.37)
        right = observation(record_id="123", lat=15.00, lon=102.00)
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.SAME_ENTITY)
        self.assertEqual(decision.score, 100)
        self.assertIn(ResolutionSignal.SAME_SOURCE_RECORD, decision.signals)

    def test_43_identical_candidate_fingerprint_is_same_entity(self):
        left = observation(source_type=SourceType.OSM, source_name="OSM", lat=14.05, lon=101.37, province="ปราจีนบุรี")
        right = observation(source_type=SourceType.WEB, source_name="Web", lat=14.05, lon=101.37, province="ปราจีนบุรี")
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.SAME_ENTITY)
        self.assertIn(ResolutionSignal.SAME_CANDIDATE_KEY, decision.signals)

    def test_44_same_phone_cross_source_can_match(self):
        left = observation(phone="081-234-5678", province="ปราจีนบุรี")
        right = observation(source_type=SourceType.WEB, source_name="Web", name="ร้านเอ", phone="081 234 5678", province="ปราจีนบุรี")
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.SAME_ENTITY)
        self.assertIn(ResolutionSignal.SAME_PHONE, decision.signals)

    def test_45_same_website_normalizes_scheme_www_and_trailing_slash(self):
        left = observation(website="https://www.example.com/shop/")
        right = observation(source_type=SourceType.WEB, source_name="Web", name="A Shop", website="http://example.com/shop")
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.SAME_ENTITY)
        self.assertIn(ResolutionSignal.SAME_WEBSITE, decision.signals)

    def test_46_same_name_and_near_location_is_same_entity(self):
        left = observation(lat=14.05000, lon=101.37000)
        right = observation(source_type=SourceType.WEB, source_name="Web", lat=14.05050, lon=101.37050)
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.SAME_ENTITY)
        self.assertIn(ResolutionSignal.NEAR_LOCATION, decision.signals)

    def test_47_similar_name_and_near_location_routes_to_review(self):
        left = observation(name="บ้านเจสุขใจ", lat=14.05, lon=101.37)
        right = observation(source_type=SourceType.WEB, source_name="Web", name="บ้านเจ สุขใจ สาขาหลัก", lat=14.0502, lon=101.3702)
        decision = EntityResolutionEngine(ResolutionPolicy(similar_name_ratio=0.65)).compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.REVIEW)
        self.assertFalse(decision.may_auto_link)

    def test_48_same_name_without_location_or_contact_requires_review(self):
        left = observation(name="ร้านกลางเมือง")
        right = observation(source_type=SourceType.WEB, source_name="Web", name="ร้านกลางเมือง")
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.REVIEW)

    def test_49_same_name_far_apart_is_distinct(self):
        left = observation(name="Cafe A", lat=13.75, lon=100.50)
        right = observation(source_type=SourceType.WEB, source_name="Web", name="Cafe A", lat=14.05, lon=101.37)
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.DISTINCT)
        self.assertIn(ResolutionSignal.FAR_LOCATION, decision.signals)

    def test_50_province_conflict_prevents_name_only_merge(self):
        left = observation(name="ร้าน A", province="ปราจีนบุรี")
        right = observation(source_type=SourceType.WEB, source_name="Web", name="ร้าน A", province="ชลบุรี")
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.DISTINCT)
        self.assertFalse(decision.may_auto_link)

    def test_51_strong_contact_with_geo_conflict_routes_to_review(self):
        left = observation(name="ร้าน A", phone="0812345678", lat=13.75, lon=100.50)
        right = observation(source_type=SourceType.WEB, source_name="Web", name="Another Name", phone="0812345678", lat=14.05, lon=101.37)
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.REVIEW)
        self.assertFalse(decision.may_auto_link)

    def test_52_unrelated_records_are_insufficient_not_forced_distinct(self):
        left = observation(name="ร้าน A")
        right = observation(source_type=SourceType.WEB, source_name="Web", name="ร้าน B")
        decision = EntityResolutionEngine().compare(left, right)
        self.assertEqual(decision.outcome, ResolutionOutcome.INSUFFICIENT_EVIDENCE)
        self.assertFalse(decision.may_auto_link)

    def test_53_policy_validation_rejects_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            ResolutionPolicy(near_distance_m=0)
        with self.assertRaises(ValueError):
            ResolutionPolicy(near_distance_m=500, far_distance_m=100)

    def test_54_resolution_is_side_effect_free(self):
        left = observation(name="ร้าน A", phone="0812345678")
        right = observation(source_type=SourceType.WEB, source_name="Web", name="ร้านเอ", phone="0812345678")
        left_before = left
        right_before = right
        EntityResolutionEngine().compare(left, right)
        self.assertEqual(left, left_before)
        self.assertEqual(right, right_before)


if __name__ == "__main__":
    unittest.main()
