from __future__ import annotations

import inspect
import unittest

from place_platform_v2 import transition_publication_boundary_v1 as boundary


class TransitionPublicationBoundaryV1Tests(unittest.TestCase):
    def test_known_taxonomy_mapping_is_deterministic(self):
        self.assertEqual(boundary.presentation_category_label("fuel"), "ปั๊มน้ำมัน")
        self.assertEqual(boundary.presentation_category_label("temple"), "วัด / ศาสนสถาน")
        self.assertEqual(boundary.presentation_category_label("restaurant"), "ร้านอาหาร")
        self.assertEqual(boundary.presentation_category_label("cafe"), "คาเฟ่")
        self.assertEqual(boundary.presentation_category_label("attraction"), "สถานที่ท่องเที่ยว")

    def test_unknown_category_is_preserved_not_invented(self):
        self.assertEqual(boundary.presentation_category_label("future_service"), "future_service")
        with self.assertRaises(ValueError):
            boundary.presentation_category_label("   ")

    def test_category_list_preserves_order_and_deduplicates(self):
        self.assertEqual(
            boundary.presentation_categories(("restaurant", "cafe", "restaurant")),
            ("ร้านอาหาร", "คาเฟ่"),
        )

    def test_legacy_address_is_display_only_fallback(self):
        result = boundary.select_display_address(
            canonical_address=None,
            legacy_published_address=" ตำบล หน้าเมือง   อำเภอ เมือง  ปราจีนบุรี ",
        )
        self.assertEqual(result.source, boundary.DisplayAddressSource.LEGACY_PUBLISHED_FALLBACK)
        self.assertFalse(result.evidence_eligible)
        self.assertEqual(result.text, "ตำบล หน้าเมือง อำเภอ เมือง ปราจีนบุรี")

    def test_canonical_address_wins_but_boundary_still_does_not_create_evidence(self):
        result = boundary.select_display_address(
            canonical_address="canonical address",
            legacy_published_address="legacy address",
        )
        self.assertEqual(result.source, boundary.DisplayAddressSource.CANONICAL)
        self.assertEqual(result.text, "canonical address")
        self.assertFalse(result.evidence_eligible)

    def test_legacy_baseline_read_allowed(self):
        decision = boundary.authorize_boundary_operation(
            boundary.BoundaryOperation.READ_LEGACY_BASELINE
        )
        self.assertTrue(decision.allowed)

    def test_all_legacy_write_or_promotion_paths_are_denied(self):
        denied = (
            boundary.BoundaryOperation.WRITE_LEGACY_BUNDLE,
            boundary.BoundaryOperation.WRITE_CANONICAL_FROM_LEGACY,
            boundary.BoundaryOperation.PROMOTE_LEGACY_LIFECYCLE,
            boundary.BoundaryOperation.CREATE_EVIDENCE_FROM_LEGACY_PRESENTATION,
        )
        for operation in denied:
            with self.subTest(operation=operation):
                self.assertFalse(boundary.authorize_boundary_operation(operation).allowed)
                with self.assertRaises(boundary.TransitionBoundaryViolation):
                    boundary.require_boundary_operation(operation)

    def test_unknown_operation_fails_closed(self):
        self.assertFalse(
            boundary.authorize_boundary_operation("not-a-real-operation").allowed
        )

    def test_baseline_count_guard(self):
        boundary.assert_legacy_baseline_count(923)
        with self.assertRaises(boundary.TransitionBoundaryViolation):
            boundary.assert_legacy_baseline_count(922)

    def test_module_has_no_database_or_writer_authority(self):
        source = inspect.getsource(boundary)
        forbidden = (
            "import sqlite3",
            "SQLitePlaceRepository",
            "PersistedPublishedProjectionWriterV1",
            "save_place(",
            "commit_migration_batch(",
            "upsert(",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_new_data_path_is_canonical_first(self):
        self.assertEqual(
            boundary.NEW_DATA_REQUIRED_PATH,
            (
                "candidate_evidence",
                "verification_entity_resolution",
                "canonical",
                "publication_gate",
                "published_projection",
            ),
        )
        self.assertNotIn("legacy_bundle", boundary.NEW_DATA_REQUIRED_PATH)


if __name__ == "__main__":
    unittest.main()

