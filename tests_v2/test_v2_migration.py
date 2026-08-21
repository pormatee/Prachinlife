import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from place_platform_v2.contracts import SourceType
from place_platform_v2.migration import (
    MigrationDisposition,
    V1MigrationPolicy,
    build_v1_import_report,
    convert_v1_record,
    load_v1_json,
    stable_import_key,
)


class TestV2Migration(unittest.TestCase):
    def sample(self):
        return {
            "id": "legacy-123",
            "title": " ร้าน เจ ทดสอบ ",
            "lat": "13.6901",
            "lng": "101.0702",
            "province": "ฉะเชิงเทรา",
            "category": "Vegetarian, Eat",
            "telephone": "038 000 000",
            "url": "https://example.test/place",
        }

    def test_01_stable_import_key_is_deterministic(self):
        self.assertEqual(stable_import_key("a.json", "1"), stable_import_key("a.json", "1"))
        self.assertNotEqual(stable_import_key("a.json", "1"), stable_import_key("b.json", "1"))

    def test_02_conversion_does_not_mutate_input(self):
        record = self.sample()
        before = deepcopy(record)
        convert_v1_record(record, source_file="vegetarian_index.json", record_index=0)
        self.assertEqual(record, before)

    def test_03_common_legacy_aliases_map_to_v2(self):
        item = convert_v1_record(self.sample(), source_file="vegetarian_index.json", record_index=0)
        self.assertEqual(item.disposition, MigrationDisposition.READY)
        c = item.observation.candidate
        self.assertEqual(c.name, "ร้าน เจ ทดสอบ")
        self.assertEqual(c.location.latitude, 13.6901)
        self.assertEqual(c.location.longitude, 101.0702)
        self.assertEqual(c.province, "ฉะเชิงเทรา")
        self.assertEqual(c.categories, ("eat", "vegetarian"))
        self.assertEqual(c.phone, "038 000 000")

    def test_04_migration_provenance_is_explicit(self):
        item = convert_v1_record(self.sample(), source_file="vegetarian_index.json", record_index=0)
        source = item.observation.candidate.source
        self.assertEqual(source.source_type, SourceType.OTHER)
        self.assertEqual(source.source_name, "prachinlife-v1-json")
        self.assertEqual(source.source_record_id, "vegetarian_index.json#legacy-123")

    def test_05_import_key_is_preserved_in_raw_attributes(self):
        item = convert_v1_record(self.sample(), source_file="vegetarian_index.json", record_index=0)
        attrs = item.observation.candidate.raw_attributes
        self.assertEqual(attrs["import_key"], item.import_key)
        self.assertEqual(attrs["migration_policy_version"], "v1-json-import-1")

    def test_06_missing_name_is_invalid_not_guessed(self):
        item = convert_v1_record({"lat": 1, "lng": 2}, source_file="x.json", record_index=0)
        self.assertEqual(item.disposition, MigrationDisposition.INVALID)
        self.assertIsNone(item.observation)

    def test_07_invalid_coordinates_are_invalid_not_silently_dropped(self):
        item = convert_v1_record({"name": "A", "lat": 999, "lng": 2}, source_file="x.json", record_index=0)
        self.assertEqual(item.disposition, MigrationDisposition.INVALID)

    def test_08_missing_coordinates_are_allowed_for_later_resolution(self):
        item = convert_v1_record({"name": "A", "province": "ชลบุรี"}, source_file="x.json", record_index=0)
        self.assertEqual(item.disposition, MigrationDisposition.READY)
        self.assertIsNone(item.observation.candidate.location)

    def test_09_replay_is_idempotently_marked_skipped(self):
        key = stable_import_key("x.json", "legacy-123")
        report = build_v1_import_report([self.sample()], source_file="x.json", already_imported={key})
        self.assertEqual(report.skipped, 1)
        self.assertEqual(report.ready, 0)

    def test_10_duplicate_ids_inside_same_batch_do_not_double_import(self):
        report = build_v1_import_report([self.sample(), self.sample()], source_file="x.json")
        self.assertEqual(report.ready, 1)
        self.assertEqual(report.skipped, 1)

    def test_11_report_counts_are_explicit_and_dry_run_default(self):
        report = build_v1_import_report([self.sample(), {"foo": "bar"}], source_file="x.json")
        self.assertTrue(report.dry_run)
        self.assertEqual((report.total, report.ready, report.invalid), (2, 1, 1))

    def test_12_policy_is_versioned(self):
        policy = V1MigrationPolicy(policy_version="migration-2")
        item = convert_v1_record(self.sample(), source_file="x.json", record_index=0, policy=policy)
        self.assertEqual(item.observation.candidate.raw_attributes["migration_policy_version"], "migration-2")

    def test_13_load_top_level_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps([{"name": "A"}], ensure_ascii=False), encoding="utf-8")
            records = load_v1_json(path)
            self.assertEqual(records[0]["name"], "A")

    def test_14_load_common_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps({"places": [{"name": "A"}]}), encoding="utf-8")
            self.assertEqual(len(load_v1_json(path)), 1)

    def test_15_load_rejects_unsupported_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps({"meta": {"count": 1}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_v1_json(path)

    def test_16_conversion_never_creates_canonical_place(self):
        item = convert_v1_record(self.sample(), source_file="x.json", record_index=0)
        self.assertNotIn("CanonicalPlace", type(item.observation).__name__)
        self.assertFalse(hasattr(item, "place_id"))


if __name__ == "__main__":
    unittest.main()
