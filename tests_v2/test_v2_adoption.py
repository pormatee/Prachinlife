from datetime import datetime, timezone
import unittest

from place_platform_v2.adoption import (
    ADOPTABLE_FIELDS,
    AdoptionOutcome,
    AdoptionPolicy,
    apply_adoption,
    propose_adoption,
)
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.repository import InMemoryPlaceRepository
from place_platform_v2.verification import FieldVerification, VerificationOutcome, ValueSupport


NOW = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 21, 1, 0, tzinfo=timezone.utc)


def verification(place_id, field, value, outcome):
    supports = ()
    if outcome is VerificationOutcome.CONFLICTING:
        supports = (
            ValueSupport(
                value="value-a",
                source_count=1,
                evidence_count=1,
                source_types=(),
                latest_observed_at=NOW,
            ),
            ValueSupport(
                value="value-b",
                source_count=1,
                evidence_count=1,
                source_types=(),
                latest_observed_at=NOW,
            ),
        )
    return FieldVerification(
        place_id=place_id,
        field_name=field,
        outcome=outcome,
        selected_value=value,
        supports=supports,
        reason="test verification",
    )


class TestV2CanonicalAdoption(unittest.TestCase):
    def setUp(self):
        self.place = CanonicalPlace(
            identity=PlaceIdentity(),
            canonical_name="ร้านเดิม",
            location=GeoPoint(14.05, 101.37),
            province="ปราจีนบุรี",
            categories=("eat",),
            lifecycle=PlaceLifecycle.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )

    def test_01_identity_and_timestamps_are_not_adoptable_fields(self):
        self.assertNotIn("identity", ADOPTABLE_FIELDS)
        self.assertNotIn("created_at", ADOPTABLE_FIELDS)
        self.assertNotIn("updated_at", ADOPTABLE_FIELDS)

    def test_02_supported_identity_field_is_blocked_by_default(self):
        result = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.SUPPORTED,
            ),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.BLOCKED)
        self.assertFalse(result.may_apply)

    def test_03_verified_identity_field_can_be_proposed(self):
        result = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.VERIFIED,
            ),
            evidence_ids=("e1", "e2"),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.PROPOSED)
        self.assertEqual(result.evidence_ids, ("e1", "e2"))

    def test_04_supported_low_risk_contact_field_can_be_proposed(self):
        result = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "phone",
                "0812345678",
                VerificationOutcome.SUPPORTED,
            ),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.PROPOSED)

    def test_05_conflict_is_never_adoptable(self):
        result = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "phone",
                None,
                VerificationOutcome.CONFLICTING,
            ),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.BLOCKED)

    def test_06_same_value_becomes_no_change(self):
        result = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านเดิม",
                VerificationOutcome.VERIFIED,
            ),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.NO_CHANGE)

    def test_07_other_place_verification_is_blocked(self):
        other_id = PlaceIdentity().place_id
        result = propose_adoption(
            place=self.place,
            verification=verification(
                other_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.VERIFIED,
            ),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.BLOCKED)

    def test_08_unknown_field_is_blocked(self):
        result = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "publishable",
                True,
                VerificationOutcome.VERIFIED,
            ),
        )
        self.assertEqual(result.outcome, AdoptionOutcome.BLOCKED)

    def test_09_apply_is_explicit_and_creates_revision(self):
        proposal = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.VERIFIED,
            ),
            evidence_ids=("e1", "e2"),
        )
        updated, revision = apply_adoption(
            place=self.place,
            proposal=proposal,
            applied_at=LATER,
        )
        self.assertEqual(self.place.canonical_name, "ร้านเดิม")
        self.assertEqual(updated.canonical_name, "ร้านใหม่")
        self.assertEqual(updated.updated_at, LATER)
        self.assertEqual(revision.before_values["canonical_name"], "ร้านเดิม")
        self.assertEqual(revision.after_values["canonical_name"], "ร้านใหม่")
        self.assertEqual(revision.evidence_ids, ("e1", "e2"))

    def test_10_blocked_or_no_change_proposal_cannot_apply(self):
        blocked = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.SUPPORTED,
            ),
        )
        with self.assertRaises(ValueError):
            apply_adoption(place=self.place, proposal=blocked, applied_at=LATER)

    def test_11_category_adoption_is_normalized_deterministically(self):
        proposal = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "categories",
                ("vegetarian", "eat", "vegetarian"),
                VerificationOutcome.VERIFIED,
            ),
        )
        updated, _ = apply_adoption(place=self.place, proposal=proposal, applied_at=LATER)
        self.assertEqual(updated.categories, ("eat", "vegetarian"))

    def test_12_adoption_has_no_publication_authority(self):
        proposal = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.VERIFIED,
            ),
        )
        self.assertFalse(hasattr(proposal, "publishable"))
        self.assertFalse(hasattr(proposal, "publish"))

    def test_13_repository_commits_place_and_revision_together(self):
        repo = InMemoryPlaceRepository()
        repo.save_place(self.place)
        proposal = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.VERIFIED,
            ),
            evidence_ids=("e1", "e2"),
        )
        updated, revision = apply_adoption(
            place=self.place, proposal=proposal, applied_at=LATER
        )
        repo.commit_adoption(updated, revision)
        self.assertEqual(repo.get_place(self.place.identity.place_id).canonical_name, "ร้านใหม่")
        self.assertEqual(repo.list_revisions(self.place.identity.place_id), (revision,))

    def test_14_repository_rejects_revision_for_different_place(self):
        repo = InMemoryPlaceRepository()
        repo.save_place(self.place)
        proposal = propose_adoption(
            place=self.place,
            verification=verification(
                self.place.identity.place_id,
                "canonical_name",
                "ร้านใหม่",
                VerificationOutcome.VERIFIED,
            ),
        )
        updated, revision = apply_adoption(
            place=self.place, proposal=proposal, applied_at=LATER
        )
        other = CanonicalPlace(
            identity=PlaceIdentity(), canonical_name="อีกสถานที่", created_at=NOW, updated_at=NOW
        )
        repo.save_place(other)
        with self.assertRaises(ValueError):
            repo.commit_adoption(other, revision)


if __name__ == "__main__":
    unittest.main()
