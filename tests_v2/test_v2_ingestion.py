from __future__ import annotations

import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import (
    GeoPoint,
    SourcePlaceCandidate,
    SourceRef,
    SourceType,
)
from place_platform_v2.ingestion import (
    DiscoveryIngestionPipeline,
    DiscoveryRequest,
    build_claims,
    candidate_fingerprint,
    normalize_candidate,
)
from place_platform_v2.models import EvidenceKind


NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)


def source_ref(source_type=SourceType.OSM, name="OSM", record_id="123"):
    return SourceRef(
        source_type=source_type,
        source_name=name,
        source_record_id=record_id,
        observed_at=NOW,
    )


class StaticAdapter:
    def __init__(self, source_type, candidates):
        self._source_type = source_type
        self._candidates = tuple(candidates)
        self.queries = []

    @property
    def source_type(self):
        return self._source_type

    def discover(self, query):
        self.queries.append(query)
        return self._candidates


class TestV2Ingestion(unittest.TestCase):
    def test_32_request_rejects_blank_query(self):
        with self.assertRaises(ValueError):
            DiscoveryRequest("   ")

    def test_33_normalization_is_deterministic(self):
        candidate = SourcePlaceCandidate(
            source=source_ref(),
            name="  ร้าน   เจ   ตัวอย่าง  ",
            province="  ปราจีนบุรี  ",
            categories=(" Vegetarian ", "VEGETARIAN", " Jay "),
            phone="  081 234 5678  ",
        )
        first = normalize_candidate(candidate)
        second = normalize_candidate(candidate)
        self.assertEqual(first, second)
        self.assertEqual(first.name, "ร้าน เจ ตัวอย่าง")
        self.assertEqual(first.categories, ("jay", "vegetarian"))
        self.assertEqual(first.province, "ปราจีนบุรี")

    def test_34_fingerprint_is_stable_and_not_place_id(self):
        point = GeoPoint(14.05, 101.37)
        first = candidate_fingerprint(
            name="ร้าน A", location=point, province="ปราจีนบุรี"
        )
        second = candidate_fingerprint(
            name=" ร้าน   A ", location=point, province="ปราจีนบุรี"
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_35_ingestion_preserves_provenance(self):
        ref = source_ref(SourceType.WEB, "Web Search", "web-1")
        adapter = StaticAdapter(
            SourceType.WEB,
            [SourcePlaceCandidate(source=ref, name="ร้าน A")],
        )
        report = DiscoveryIngestionPipeline().ingest(
            adapter, DiscoveryRequest("ร้านเจ ปราจีนบุรี")
        )
        observation = report.observations[0]
        self.assertEqual(observation.candidate.source, ref)
        self.assertTrue(all(claim.source == ref for claim in observation.claims))

    def test_36_adapter_source_mismatch_is_rejected(self):
        candidate = SourcePlaceCandidate(
            source=source_ref(SourceType.WEB, "Web"),
            name="ร้าน A",
        )
        adapter = StaticAdapter(SourceType.OSM, [candidate])
        with self.assertRaises(ValueError):
            DiscoveryIngestionPipeline().ingest(adapter, DiscoveryRequest("A"))

    def test_37_claims_include_existence_and_name(self):
        normalized = normalize_candidate(
            SourcePlaceCandidate(source=source_ref(), name="ร้าน A")
        )
        claims = build_claims(normalized)
        by_kind = {claim.kind for claim in claims}
        self.assertIn(EvidenceKind.EXISTENCE, by_kind)
        self.assertIn(EvidenceKind.NAME, by_kind)

    def test_38_optional_fields_become_field_level_claims(self):
        normalized = normalize_candidate(
            SourcePlaceCandidate(
                source=source_ref(),
                name="ร้าน A",
                location=GeoPoint(14.05, 101.37),
                province="ปราจีนบุรี",
                categories=("vegetarian",),
                website="https://example.com",
            )
        )
        fields = {claim.field_name for claim in build_claims(normalized)}
        self.assertTrue(
            {"location", "province", "categories", "website"}.issubset(fields)
        )

    def test_39_manual_source_uses_same_pipeline(self):
        ref = source_ref(SourceType.MANUAL, "Manual Entry", "manual-1")
        adapter = StaticAdapter(
            SourceType.MANUAL,
            [
                SourcePlaceCandidate(
                    source=ref,
                    name="ร้านที่เพิ่มเอง",
                    province="ฉะเชิงเทรา",
                )
            ],
        )
        report = DiscoveryIngestionPipeline().ingest(
            adapter, DiscoveryRequest("manual import")
        )
        self.assertEqual(report.source_type, "manual")
        self.assertEqual(report.count, 1)
        self.assertEqual(report.observations[0].candidate.source.source_type, SourceType.MANUAL)

    def test_40_future_other_source_uses_same_pipeline(self):
        ref = source_ref(SourceType.OTHER, "Future API", "future-1")
        adapter = StaticAdapter(
            SourceType.OTHER,
            [SourcePlaceCandidate(source=ref, name="Future Place")],
        )
        report = DiscoveryIngestionPipeline().ingest(
            adapter, DiscoveryRequest("future")
        )
        self.assertEqual(report.source_name, "Future API")
        self.assertEqual(report.count, 1)

    def test_41_ingestion_does_not_mutate_input_raw_attributes(self):
        raw = {"tag": "original"}
        candidate = SourcePlaceCandidate(
            source=source_ref(),
            name="ร้าน A",
            raw_attributes=raw,
        )
        normalized = normalize_candidate(candidate)
        normalized.raw_attributes["tag"] = "changed"
        self.assertEqual(raw["tag"], "original")


if __name__ == "__main__":
    unittest.main()
