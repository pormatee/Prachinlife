from __future__ import annotations

import unittest
from dataclasses import fields
from datetime import datetime, timezone

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.read_model import (
    InMemoryPublishedPlaceRepository,
    PublishedNearbyQuery,
    PublishedNearbyResult,
    PublishedTextQuery,
)


def view(name, lat, lon, province="ปราจีนบุรี", categories=("eat",), place_id=None):
    return PublishedPlaceView(
        place_id=place_id or f"place-{name}",
        name=name,
        location=GeoPoint(lat, lon),
        province=province,
        categories=categories,
        lifecycle=PlaceLifecycle.ACTIVE,
        address_text=f"ที่อยู่ {name} {province}",
        publication_policy_version="1.0-packet8",
        published_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )


class TestV2ReadModel(unittest.TestCase):
    def test_01_repository_accepts_only_published_view_contract(self):
        repo = InMemoryPublishedPlaceRepository()
        place = view("ร้าน A", 14.05, 101.37)
        repo.upsert_published(place)
        self.assertEqual(repo.get_published(place.place_id), place)

    def test_02_nearby_returns_nearest_first(self):
        repo = InMemoryPublishedPlaceRepository()
        near = view("ใกล้", 14.0505, 101.3705)
        far = view("ไกล", 14.08, 101.40)
        repo.upsert_published(far)
        repo.upsert_published(near)
        results = repo.search_nearby(PublishedNearbyQuery(GeoPoint(14.05, 101.37), 20))
        self.assertEqual(tuple(item.place.name for item in results), ("ใกล้", "ไกล"))

    def test_03_nearby_respects_radius(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("ใกล้", 14.0505, 101.3705))
        repo.upsert_published(view("ไกล", 15.00, 102.00))
        results = repo.search_nearby(PublishedNearbyQuery(GeoPoint(14.05, 101.37), 5))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].place.name, "ใกล้")

    def test_04_nearby_filters_category(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("ร้านเจ", 14.0505, 101.3705, categories=("vegetarian",)))
        repo.upsert_published(view("ร้านทั่วไป", 14.0506, 101.3706, categories=("eat",)))
        results = repo.search_nearby(
            PublishedNearbyQuery(GeoPoint(14.05, 101.37), 5, categories=("vegetarian",))
        )
        self.assertEqual(tuple(item.place.name for item in results), ("ร้านเจ",))

    def test_05_nearby_filters_province(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("ปราจีน", 14.0505, 101.3705, province="ปราจีนบุรี"))
        repo.upsert_published(view("ชลบุรี", 14.0506, 101.3706, province="ชลบุรี"))
        results = repo.search_nearby(
            PublishedNearbyQuery(GeoPoint(14.05, 101.37), 5, province="ปราจีนบุรี")
        )
        self.assertEqual(tuple(item.place.name for item in results), ("ปราจีน",))

    def test_06_text_search_matches_name(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("ครัวเจสุขใจ", 14.05, 101.37, categories=("vegetarian",)))
        self.assertEqual(len(repo.search_text(PublishedTextQuery(text="สุขใจ"))), 1)

    def test_07_text_search_matches_address_or_category(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("ร้าน A", 14.05, 101.37, categories=("vegetarian",)))
        self.assertEqual(len(repo.search_text(PublishedTextQuery(text="vegetarian"))), 1)
        self.assertEqual(len(repo.search_text(PublishedTextQuery(text="ปราจีนบุรี"))), 1)

    def test_08_text_search_is_case_and_whitespace_tolerant(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("Green   Garden", 14.05, 101.37))
        self.assertEqual(len(repo.search_text(PublishedTextQuery(text="green garden"))), 1)

    def test_09_upsert_replaces_same_published_place_id(self):
        repo = InMemoryPublishedPlaceRepository()
        original = view("เดิม", 14.05, 101.37, place_id="same")
        updated = view("ใหม่", 14.05, 101.37, place_id="same")
        repo.upsert_published(original)
        repo.upsert_published(updated)
        self.assertEqual(repo.get_published("same").name, "ใหม่")

    def test_10_remove_unpublishes_from_all_searches(self):
        repo = InMemoryPublishedPlaceRepository()
        place = view("ร้าน A", 14.05, 101.37)
        repo.upsert_published(place)
        repo.remove_published(place.place_id)
        self.assertIsNone(repo.get_published(place.place_id))
        self.assertEqual(repo.search_text(PublishedTextQuery()), ())

    def test_11_search_results_expose_published_view_not_internal_fields(self):
        field_names = {item.name for item in fields(PublishedNearbyResult)}
        self.assertEqual(field_names, {"place", "distance_km"})
        published_names = {item.name for item in fields(PublishedPlaceView)}
        self.assertNotIn("evidence", published_names)
        self.assertNotIn("revisions", published_names)

    def test_12_query_validation_rejects_invalid_limits_and_radius(self):
        with self.assertRaises(ValueError):
            PublishedNearbyQuery(GeoPoint(14.05, 101.37), 0)
        with self.assertRaises(ValueError):
            PublishedTextQuery(limit=0)
        with self.assertRaises(ValueError):
            PublishedTextQuery(province="   ")

    def test_13_empty_text_query_can_list_filtered_published_places(self):
        repo = InMemoryPublishedPlaceRepository()
        repo.upsert_published(view("A", 14.05, 101.37, province="ปราจีนบุรี"))
        repo.upsert_published(view("B", 13.30, 100.90, province="ชลบุรี"))
        results = repo.search_text(PublishedTextQuery(province="ชลบุรี"))
        self.assertEqual(tuple(item.name for item in results), ("B",))


if __name__ == "__main__":
    unittest.main()
