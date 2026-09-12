from __future__ import annotations

import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint, SourcePlaceCandidate, SourceRef, SourceType
from place_platform_v2.discovery_resolution import CanonicalResolutionOrchestrator, DiscoveryResolutionOutcome
from place_platform_v2.entity_resolution import ResolutionDecision, ResolutionOutcome, ResolutionSignal
from place_platform_v2.ingestion import IngestionObservation, build_claims, normalize_candidate
from place_platform_v2.models import CanonicalPlace, PlaceIdentity

NOW = datetime(2026, 9, 12, tzinfo=timezone.utc)
P1 = "11111111-1111-4111-8111-111111111111"
P2 = "22222222-2222-4222-8222-222222222222"

def place(pid, name):
    return CanonicalPlace(
        identity=PlaceIdentity(pid),
        canonical_name=name,
        location=GeoPoint(14.05, 101.37),
        province="ปราจีนบุรี",
        categories=("restaurant",),
        created_at=NOW,
        updated_at=NOW,
    )

def observation():
    c = normalize_candidate(SourcePlaceCandidate(
        source=SourceRef(SourceType.OSM, "OpenStreetMap", source_record_id="node/999", observed_at=NOW),
        name="ร้านทดสอบ",
        location=GeoPoint(14.05, 101.37),
        province="ปราจีนบุรี",
        categories=("restaurant",),
    ))
    return IngestionObservation(c, build_claims(c))

def dec(outcome, score, *signals):
    return ResolutionDecision(outcome=outcome, score=score, signals=tuple(signals), reason="test")

class FakeEngine:
    def __init__(self, decisions):
        self.decisions = decisions
    def compare(self, left, right):
        return self.decisions[right.candidate.source.source_record_id]

class Tests(unittest.TestCase):
    def run_case(self, decisions, places):
        return CanonicalResolutionOrchestrator(FakeEngine(decisions)).resolve_one(observation(), places)

    def test_single_same(self):
        r=self.run_case({P1:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME)},[place(P1,"ร้านทดสอบ")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.MATCHED)

    def test_same_plus_proximity_only_review_matches(self):
        r=self.run_case({
            P1:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME,ResolutionSignal.NEAR_LOCATION),
            P2:dec(ResolutionOutcome.REVIEW,40,ResolutionSignal.NEAR_LOCATION),
        },[place(P1,"ร้านทดสอบ"),place(P2,"ร้านข้างเคียง")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.MATCHED)
        self.assertEqual(r.matched_place_id,P1)
        self.assertIn("proximity-only",r.reason)

    def test_identity_review_blocks(self):
        r=self.run_case({
            P1:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME,ResolutionSignal.NEAR_LOCATION),
            P2:dec(ResolutionOutcome.REVIEW,70,ResolutionSignal.SIMILAR_NAME,ResolutionSignal.NEAR_LOCATION),
        },[place(P1,"ร้านทดสอบ"),place(P2,"ร้านทดสอบสาขา")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.REVIEW)

    def test_multiple_same_blocks(self):
        r=self.run_case({
            P1:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME),
            P2:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME),
        },[place(P1,"ร้านทดสอบ"),place(P2,"ร้านทดสอบ")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.REVIEW)

    def test_review_without_same_stays_review(self):
        r=self.run_case({P1:dec(ResolutionOutcome.REVIEW,40,ResolutionSignal.NEAR_LOCATION)},[place(P1,"ร้านข้างเคียง")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.REVIEW)

    def test_none_stays_new(self):
        r=self.run_case({P1:dec(ResolutionOutcome.INSUFFICIENT_EVIDENCE,0,ResolutionSignal.SAME_PROVINCE)},[place(P1,"ร้านอื่น")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.NEW)

    def test_phone_review_blocks(self):
        r=self.run_case({
            P1:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME),
            P2:dec(ResolutionOutcome.REVIEW,60,ResolutionSignal.SAME_PHONE,ResolutionSignal.FAR_LOCATION),
        },[place(P1,"ร้านทดสอบ"),place(P2,"ร้านอื่น")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.REVIEW)

    def test_website_review_blocks(self):
        r=self.run_case({
            P1:dec(ResolutionOutcome.SAME_ENTITY,90,ResolutionSignal.SAME_NAME),
            P2:dec(ResolutionOutcome.REVIEW,60,ResolutionSignal.SAME_WEBSITE,ResolutionSignal.FAR_LOCATION),
        },[place(P1,"ร้านทดสอบ"),place(P2,"ร้านอื่น")])
        self.assertEqual(r.outcome, DiscoveryResolutionOutcome.REVIEW)

if __name__ == "__main__":
    unittest.main()
