from __future__ import annotations

import unittest
from dataclasses import fields
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.publication import (
    PublicationOutcome,
    PublicationPolicy,
    PublishedPlaceView,
    build_published_view,
    evaluate_publication,
)
from place_platform_v2.verification import FieldVerification, VerificationOutcome, ValueSupport


def verified(place, field_name, value):
    support = ValueSupport(
        value=value,
        source_count=2,
        evidence_count=2,
        source_types=(),
        latest_observed_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )
    return FieldVerification(
        place_id=place.identity.place_id,
        field_name=field_name,
        outcome=VerificationOutcome.VERIFIED,
        selected_value=value,
        supports=(support,),
        reason="verified fixture",
    )


def supported(place, field_name, value):
    support = ValueSupport(
        value=value,
        source_count=1,
        evidence_count=1,
        source_types=(),
        latest_observed_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )
    return FieldVerification(
        place_id=place.identity.place_id,
        field_name=field_name,
        outcome=VerificationOutcome.SUPPORTED,
        selected_value=value,
        supports=(support,),
        reason="supported fixture",
    )


def active_place():
    return CanonicalPlace(
        identity=PlaceIdentity(),
        canonical_name="ร้านตัวอย่าง",
        location=GeoPoint(14.05, 101.37),
        address_text="ปราจีนบุรี",
        province="ปราจีนบุรี",
        categories=("vegetarian",),
        phone="037000000",
        website="https://example.test",
        lifecycle=PlaceLifecycle.ACTIVE,
    )


def required_verifications(place):
    return tuple(
        verified(place, field_name, getattr(place, field_name))
        for field_name in sorted(PublicationPolicy().required_verified_fields)
    )


class TestV2Publication(unittest.TestCase):
    def test_01_complete_verified_active_place_is_eligible(self):
        place = active_place()
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        self.assertEqual(decision.outcome, PublicationOutcome.ELIGIBLE)
        self.assertTrue(decision.may_publish)

    def test_02_missing_required_verification_is_blocked(self):
        place = active_place()
        verifications = tuple(v for v in required_verifications(place) if v.field_name != "location")
        decision = evaluate_publication(place=place, verifications=verifications)
        self.assertEqual(decision.outcome, PublicationOutcome.BLOCKED)
        self.assertIn("missing verification for location", decision.reasons)

    def test_03_supported_is_not_enough_for_required_publication_field(self):
        place = active_place()
        verifications = list(required_verifications(place))
        verifications = [supported(place, "province", place.province) if v.field_name == "province" else v for v in verifications]
        decision = evaluate_publication(place=place, verifications=verifications)
        self.assertFalse(decision.may_publish)

    def test_04_verification_must_match_canonical_value(self):
        place = active_place()
        verifications = list(required_verifications(place))
        verifications = [verified(place, "province", "ชลบุรี") if v.field_name == "province" else v for v in verifications]
        decision = evaluate_publication(place=place, verifications=verifications)
        self.assertIn("province verification does not match canonical value", decision.reasons)

    def test_05_non_active_place_is_blocked(self):
        base = active_place()
        place = CanonicalPlace(
            identity=base.identity,
            canonical_name=base.canonical_name,
            location=base.location,
            province=base.province,
            categories=base.categories,
            lifecycle=PlaceLifecycle.CLOSED,
        )
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        self.assertIn("canonical lifecycle is not active", decision.reasons)

    def test_06_missing_location_is_blocked(self):
        base = active_place()
        place = CanonicalPlace(
            identity=base.identity,
            canonical_name=base.canonical_name,
            location=None,
            province=base.province,
            categories=base.categories,
            lifecycle=base.lifecycle,
        )
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        self.assertIn("canonical location is missing", decision.reasons)

    def test_07_missing_categories_is_blocked(self):
        base = active_place()
        place = CanonicalPlace(
            identity=base.identity,
            canonical_name=base.canonical_name,
            location=base.location,
            province=base.province,
            categories=(),
            lifecycle=base.lifecycle,
        )
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        self.assertIn("canonical categories are missing", decision.reasons)

    def test_08_wrong_place_verifications_do_not_count(self):
        place = active_place()
        other = active_place()
        decision = evaluate_publication(place=place, verifications=required_verifications(other))
        self.assertFalse(decision.may_publish)

    def test_09_blocked_decision_cannot_build_view(self):
        place = active_place()
        decision = evaluate_publication(place=place, verifications=())
        with self.assertRaises(ValueError):
            build_published_view(place=place, decision=decision)

    def test_10_eligible_decision_builds_consumer_view(self):
        place = active_place()
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        view = build_published_view(place=place, decision=decision)
        self.assertEqual(view.place_id, place.identity.place_id)
        self.assertEqual(view.name, place.canonical_name)
        self.assertEqual(view.categories, place.categories)

    def test_11_published_view_excludes_internal_evidence_and_revision_fields(self):
        names = {item.name for item in fields(PublishedPlaceView)}
        self.assertNotIn("evidence", names)
        self.assertNotIn("evidence_ids", names)
        self.assertNotIn("revisions", names)
        self.assertNotIn("source", names)

    def test_12_publication_does_not_mutate_canonical_place(self):
        place = active_place()
        before = place
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        build_published_view(place=place, decision=decision)
        self.assertEqual(place, before)

    def test_13_publication_policy_is_versioned(self):
        self.assertEqual(PublicationPolicy().policy_version, "1.0-packet8")

    def test_14_naive_published_at_is_rejected(self):
        place = active_place()
        decision = evaluate_publication(place=place, verifications=required_verifications(place))
        with self.assertRaises(ValueError):
            build_published_view(
                place=place,
                decision=decision,
                published_at=datetime(2026, 8, 21),
            )


if __name__ == "__main__":
    unittest.main()
