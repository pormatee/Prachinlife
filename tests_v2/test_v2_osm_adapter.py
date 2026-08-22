from __future__ import annotations

import unittest
from datetime import datetime, timezone

from place_platform_v2.contracts import SourceType
from place_platform_v2.ingestion import (
    DiscoveryIngestionPipeline,
    DiscoveryRequest,
)
from place_platform_v2.osm_adapter import (
    OSMPlaceAdapterV2,
    element_to_candidate,
    osm_record_id,
)


NOW = datetime(2026, 8, 21, tzinfo=timezone.utc)


def node(
    element_id=123,
    *,
    name="ร้านเจสุขใจ",
    lat=14.05,
    lon=101.37,
    extra_tags=None,
):
    tags = {
        "name": name,
        "amenity": "restaurant",
        "addr:province": "ปราจีนบุรี",
    }
    tags.update(extra_tags or {})

    return {
        "type": "node",
        "id": element_id,
        "lat": lat,
        "lon": lon,
        "tags": tags,
    }


class TestV2OSMAdapter(unittest.TestCase):

    def test_183_record_id_is_stable(self):
        self.assertEqual(
            osm_record_id(node()),
            "node/123",
        )

    def test_184_invalid_element_identity_rejected(self):
        with self.assertRaises(ValueError):
            osm_record_id({"type": "unknown", "id": 1})

        with self.assertRaises(ValueError):
            osm_record_id({"type": "node"})

    def test_185_candidate_preserves_osm_provenance(self):
        candidate = element_to_candidate(
            node(),
            observed_at=NOW,
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(
            candidate.source.source_type,
            SourceType.OSM,
        )
        self.assertEqual(
            candidate.source.source_record_id,
            "node/123",
        )
        self.assertEqual(
            candidate.source.source_name,
            "OpenStreetMap",
        )
        self.assertEqual(
            candidate.raw_attributes["osm_id"],
            123,
        )

    def test_186_coordinates_are_preserved(self):
        candidate = element_to_candidate(
            node(),
            observed_at=NOW,
        )

        self.assertEqual(
            candidate.location.latitude,
            14.05,
        )
        self.assertEqual(
            candidate.location.longitude,
            101.37,
        )

    def test_187_way_center_is_supported(self):
        element = {
            "type": "way",
            "id": 456,
            "center": {
                "lat": 14.06,
                "lon": 101.38,
            },
            "tags": {
                "name": "Cafe A",
                "amenity": "cafe",
            },
        }

        candidate = element_to_candidate(
            element,
            observed_at=NOW,
        )

        self.assertEqual(
            candidate.source.source_record_id,
            "way/456",
        )
        self.assertEqual(
            candidate.location.latitude,
            14.06,
        )

    def test_188_unnamed_element_is_not_candidate(self):
        element = node()
        element["tags"].pop("name")

        self.assertIsNone(
            element_to_candidate(
                element,
                observed_at=NOW,
            )
        )

    def test_189_food_categories_are_mapped(self):
        candidate = element_to_candidate(
            node(),
            observed_at=NOW,
        )

        self.assertIn("eat", candidate.categories)
        self.assertIn(
            "restaurant",
            candidate.categories,
        )

    def test_190_vegetarian_tags_are_mapped(self):
        candidate = element_to_candidate(
            node(
                extra_tags={
                    "diet:vegetarian": "yes",
                    "diet:vegan": "yes",
                }
            ),
            observed_at=NOW,
        )

        self.assertIn(
            "vegetarian",
            candidate.categories,
        )
        self.assertIn(
            "vegan",
            candidate.categories,
        )

    def test_191_contact_fields_are_preserved(self):
        candidate = element_to_candidate(
            node(
                extra_tags={
                    "phone": "0812345678",
                    "website": "https://example.com",
                }
            ),
            observed_at=NOW,
        )

        self.assertEqual(
            candidate.phone,
            "0812345678",
        )
        self.assertEqual(
            candidate.website,
            "https://example.com",
        )

    def test_192_adapter_output_is_deterministic(self):
        elements = (
            node(2, name="B"),
            node(1, name="A"),
        )

        adapter = OSMPlaceAdapterV2(
            elements,
            observed_at=NOW,
        )

        first = adapter.discover("restaurants")
        second = adapter.discover("restaurants")

        self.assertEqual(first, second)
        self.assertEqual(
            [
                item.source.source_record_id
                for item in first
            ],
            ["node/1", "node/2"],
        )

    def test_193_adapter_uses_standard_ingestion(self):
        adapter = OSMPlaceAdapterV2(
            (node(),),
            observed_at=NOW,
        )

        report = DiscoveryIngestionPipeline().ingest(
            adapter,
            DiscoveryRequest("restaurants"),
        )

        self.assertEqual(report.count, 1)
        self.assertEqual(
            report.source_type,
            "osm",
        )

        observation = report.observations[0]

        self.assertEqual(
            observation.candidate.source.source_record_id,
            "node/123",
        )

        fields = {
            claim.field_name
            for claim in observation.claims
        }

        self.assertIn("existence", fields)
        self.assertIn("canonical_name", fields)
        self.assertIn("location", fields)
        self.assertIn("province", fields)
        self.assertIn("categories", fields)

    def test_194_adapter_has_no_persistence_or_publication_api(self):
        adapter = OSMPlaceAdapterV2(
            (),
            observed_at=NOW,
        )

        self.assertFalse(hasattr(adapter, "save"))
        self.assertFalse(hasattr(adapter, "publish"))
        self.assertFalse(hasattr(adapter, "repository"))


if __name__ == "__main__":
    unittest.main()
