from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timezone

from place_platform_v2 import prachinburi_expansion_intake_v1 as policy
from place_platform_v2.adoption import AdoptionPolicy
from place_platform_v2.contracts import GeoPoint, SourcePlaceCandidate, SourceRef, SourceType
from place_platform_v2.verification import VerificationPolicy


def candidate(
    *,
    province="ปราจีนบุรี",
    categories=("restaurant",),
    location=GeoPoint(14.05, 101.37),
    source_record_id="place-1",
    source_url=None,
):
    return SourcePlaceCandidate(
        source=SourceRef(
            source_type=SourceType.OFFICIAL,
            source_name="test-source",
            source_record_id=source_record_id,
            source_url=source_url,
            observed_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        ),
        name="ร้านทดสอบ",
        province=province,
        categories=categories,
        location=location,
    )


class PrachinburiExpansionIntakeV1Tests(unittest.TestCase):
    def test_target_baselines_and_floors(self):
        targets = policy.expansion_targets()
        self.assertEqual(targets["restaurant"].audited_baseline, 30)
        self.assertEqual(targets["cafe"].audited_baseline, 25)
        self.assertEqual(targets["vegetarian"].audited_baseline, 2)
        self.assertGreater(targets["restaurant"].target_floor, 30)

    def test_gas_is_not_an_expansion_target(self):
        self.assertNotIn("fuel", policy.expansion_targets())
        self.assertEqual(policy.target_gap("fuel"), 0)

    def test_high_value_targets_prioritized(self):
        codes = policy.prioritized_target_codes()
        self.assertLess(codes.index("restaurant"), codes.index("park"))
        self.assertLess(codes.index("vegetarian"), codes.index("park"))

    def test_traceable_prachinburi_target_candidate_is_eligible(self):
        result = policy.assess_candidate(candidate())
        self.assertEqual(result.outcome, policy.IntakeOutcome.ELIGIBLE_FOR_RESOLUTION)
        self.assertTrue(result.near_me_ready)
        self.assertTrue(result.may_enter_entity_resolution)

    def test_source_url_can_supply_traceability(self):
        result = policy.assess_candidate(
            candidate(source_record_id=None, source_url="https://example.test/place/1")
        )
        self.assertEqual(result.outcome, policy.IntakeOutcome.ELIGIBLE_FOR_RESOLUTION)

    def test_missing_traceability_is_held(self):
        result = policy.assess_candidate(candidate(source_record_id=None, source_url=None))
        self.assertEqual(result.outcome, policy.IntakeOutcome.HOLD_FOR_ENRICHMENT)
        self.assertFalse(result.may_enter_entity_resolution)

    def test_missing_coordinates_is_held(self):
        result = policy.assess_candidate(candidate(location=None))
        self.assertEqual(result.outcome, policy.IntakeOutcome.HOLD_FOR_ENRICHMENT)
        self.assertFalse(result.near_me_ready)

    def test_wrong_province_is_rejected(self):
        result = policy.assess_candidate(candidate(province="ชลบุรี"))
        self.assertEqual(result.outcome, policy.IntakeOutcome.REJECT_OUT_OF_SCOPE)

    def test_non_target_category_is_rejected(self):
        result = policy.assess_candidate(candidate(categories=("fuel",)))
        self.assertEqual(result.outcome, policy.IntakeOutcome.REJECT_OUT_OF_SCOPE)

    def test_multicategory_candidate_matches_only_targets(self):
        result = policy.assess_candidate(candidate(categories=("restaurant", "attraction", "fuel")))
        self.assertEqual(
            result.matched_target_categories,
            ("restaurant", "attraction"),
        )

    def test_legacy_presentation_is_not_new_evidence(self):
        result = policy.assess_candidate(
            candidate(),
            origin=policy.CandidateOrigin.LEGACY_PRESENTATION,
        )
        self.assertEqual(result.outcome, policy.IntakeOutcome.REJECT_LEGACY_PRESENTATION)

    def test_existing_verification_threshold_is_not_lowered(self):
        verification = VerificationPolicy()
        adoption = AdoptionPolicy()
        self.assertEqual(verification.verified_independent_sources, 2)
        self.assertTrue(
            {"canonical_name", "location", "province", "categories", "lifecycle"}
            <= adoption.verified_required_fields
        )

    def test_required_path_does_not_use_legacy_bundle(self):
        self.assertNotIn("legacy_bundle", policy.NEW_DATA_REQUIRED_PATH)
        self.assertLess(
            policy.NEW_DATA_REQUIRED_PATH.index("entity_resolution_dedup"),
            policy.NEW_DATA_REQUIRED_PATH.index("canonical"),
        )

    def test_module_has_no_database_write_authority(self):
        source = inspect.getsource(policy)
        forbidden = (
            "import sqlite3",
            "SQLitePlaceRepository",
            "save_place(",
            "commit_adoption(",
            "PersistedPublishedProjectionWriterV1",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()

