import unittest

from place_platform_v2.migration import MigrationDisposition, convert_v1_record


class TestV2ProductionMapping(unittest.TestCase):
    def test_01_nested_location_maps_province_and_coordinates(self):
        item = convert_v1_record({
            "id": "go-1", "title": "Place A", "category": "attraction",
            "location": {"province": "ปราจีนบุรี", "latitude": 14.1, "longitude": 101.3},
        }, source_file="go_index.json", record_index=0)
        c = item.observation.candidate
        self.assertEqual(c.province, "ปราจีนบุรี")
        self.assertEqual((c.location.latitude, c.location.longitude), (14.1, 101.3))

    def test_02_vegetarian_food_types_map_to_categories(self):
        item = convert_v1_record({
            "id": "veg-1", "title": "Veg A", "food_types": ["vegetarian", "vegan"],
            "location": {"province": "กระบี่", "latitude": 7.57, "longitude": 99.03},
        }, source_file="vegetarian_index.json", record_index=0)
        self.assertEqual(item.observation.candidate.categories, ("vegan", "vegetarian"))

    def test_03_metadata_phone_and_website_are_fallbacks(self):
        item = convert_v1_record({
            "title": "Clinic A", "category": "clinic",
            "location": {"province": "ปราจีนบุรี", "latitude": 13.9, "longitude": 101.5},
            "metadata": {"phone": "037000000", "website": "https://example.test"},
        }, source_file="service_index.json", record_index=0)
        c = item.observation.candidate
        self.assertEqual(c.phone, "037000000")
        self.assertEqual(c.website, "https://example.test")

    def test_04_top_level_contact_wins_over_metadata(self):
        item = convert_v1_record({
            "title": "Clinic A", "category": "clinic", "phone": "111",
            "metadata": {"phone": "222"},
        }, source_file="service_index.json", record_index=0)
        self.assertEqual(item.observation.candidate.phone, "111")

    def test_05_explicit_shopping_record_is_skipped(self):
        item = convert_v1_record({
            "id": "deal-1", "title": "Lotus Deal", "category": "shopping",
            "content_type": "deal",
            "location": {"scope": "national", "country": "TH", "latitude": None, "longitude": None},
        }, source_file="prachinlife_index.json", record_index=0)
        self.assertEqual(item.disposition, MigrationDisposition.SKIPPED)
        self.assertEqual(item.reason, "explicit non-place content")
        self.assertIsNone(item.observation)

    def test_06_missing_coordinates_does_not_skip_a_real_place(self):
        item = convert_v1_record({
            "title": "Restaurant A", "category": "eat",
            "location": {"province": "ปราจีนบุรี", "latitude": None, "longitude": None},
        }, source_file="prachinlife_index.json", record_index=0)
        self.assertEqual(item.disposition, MigrationDisposition.READY)
        self.assertEqual(item.observation.candidate.province, "ปราจีนบุรี")
        self.assertIsNone(item.observation.candidate.location)

    def test_07_nested_location_missing_province_remains_unknown(self):
        item = convert_v1_record({
            "title": "Place A", "category": "attraction",
            "location": {"latitude": 14.1, "longitude": 101.3},
        }, source_file="go_index.json", record_index=0)
        self.assertIsNone(item.observation.candidate.province)

    def test_08_mapping_keeps_full_legacy_record_for_provenance(self):
        record = {
            "id": "veg-1", "title": "Veg A", "food_types": ["vegetarian"],
            "location": {"province": "กระบี่", "latitude": 7.5, "longitude": 99.0},
            "metadata": {"verified": False},
        }
        item = convert_v1_record(record, source_file="vegetarian_index.json", record_index=0)
        self.assertEqual(item.observation.candidate.raw_attributes["legacy_record"], record)


if __name__ == "__main__":
    unittest.main()
