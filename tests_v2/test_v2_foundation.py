import importlib
import unittest
from datetime import datetime, timezone


class TestV2Foundation(unittest.TestCase):
    def test_01_v2_namespace_imports(self):
        mod = importlib.import_module("place_platform_v2")
        self.assertEqual(mod.PLATFORM_VERSION, "2.0.0-dev")

    def test_02_frozen_v1_baseline_is_exact_and_immutable(self):
        from place_platform_v2.baseline import V1_BASELINE

        self.assertEqual(V1_BASELINE.tag, "prachinlife-platform-v1")
        self.assertEqual(
            V1_BASELINE.commit,
            "6810d4c7e6ba88d911162720b715d2ee7528cf7f",
        )
        self.assertFalse(V1_BASELINE.mutable)

    def test_03_geo_validation_accepts_thailand_like_coordinates(self):
        from place_platform_v2.contracts import GeoPoint

        point = GeoPoint(latitude=13.6904, longitude=101.0779)
        self.assertEqual(point.latitude, 13.6904)

    def test_04_geo_validation_rejects_invalid_coordinates(self):
        from place_platform_v2.contracts import GeoPoint

        with self.assertRaises(ValueError):
            GeoPoint(latitude=95.0, longitude=101.0)

    def test_05_candidate_requires_source_and_name(self):
        from place_platform_v2.contracts import (
            SourcePlaceCandidate,
            SourceRef,
            SourceType,
        )

        source = SourceRef(
            source_type=SourceType.MANUAL,
            source_name="manual_seed",
            observed_at=datetime.now(timezone.utc),
        )
        candidate = SourcePlaceCandidate(source=source, name="ร้านตัวอย่าง")
        self.assertEqual(candidate.source.source_type, SourceType.MANUAL)

    def test_06_blank_candidate_name_is_rejected(self):
        from place_platform_v2.contracts import (
            SourcePlaceCandidate,
            SourceRef,
            SourceType,
        )

        source = SourceRef(
            source_type=SourceType.WEB,
            source_name="web_discovery",
        )
        with self.assertRaises(ValueError):
            SourcePlaceCandidate(source=source, name="   ")

    def test_07_future_source_types_can_use_other_without_core_patch(self):
        from place_platform_v2.contracts import SourceType

        self.assertEqual(SourceType.OTHER.value, "other")

    def test_08_discovery_does_not_equal_publication(self):
        from place_platform_v2.contracts import EvidenceStatus, PublishDecision

        decision = PublishDecision(
            status=EvidenceStatus.CANDIDATE,
            publishable=False,
            reason="discovery evidence requires verification",
        )
        self.assertFalse(decision.publishable)

    def test_09_rejected_or_candidate_cannot_be_publishable(self):
        from place_platform_v2.contracts import EvidenceStatus, PublishDecision

        for status in (EvidenceStatus.CANDIDATE, EvidenceStatus.REJECTED):
            with self.assertRaises(ValueError):
                PublishDecision(
                    status=status,
                    publishable=True,
                    reason="must fail",
                )

    def test_10_supported_or_verified_may_be_publishable(self):
        from place_platform_v2.contracts import EvidenceStatus, PublishDecision

        for status in (EvidenceStatus.SUPPORTED, EvidenceStatus.VERIFIED):
            decision = PublishDecision(
                status=status,
                publishable=True,
                reason="passes explicit publish policy",
            )
            self.assertTrue(decision.publishable)


if __name__ == "__main__":
    unittest.main()
