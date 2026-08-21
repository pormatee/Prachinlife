import json
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.migration_audit import audit_v1_files, discover_v1_place_json


class TestV2MigrationAudit(unittest.TestCase):
    def write_json(self, root, name, payload):
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_01_audit_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A", "lat": 13, "lng": 101}])
            before = p.read_bytes()
            audit_v1_files([p])
            self.assertEqual(p.read_bytes(), before)

    def test_02_counts_ready_and_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A"}, {"foo": "bar"}])
            r = audit_v1_files([p])
            self.assertEqual((r.total_records, r.ready_records, r.invalid_records), (2, 1, 1))

    def test_03_missing_location_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A", "province": "ชลบุรี"}])
            f = audit_v1_files([p]).files[0]
            self.assertEqual(f.missing_location, 1)

    def test_04_missing_province_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A", "lat": 13, "lng": 101}])
            self.assertEqual(audit_v1_files([p]).files[0].missing_province, 1)

    def test_05_missing_categories_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A"}])
            self.assertEqual(audit_v1_files([p]).files[0].missing_categories, 1)

    def test_06_province_coverage_is_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A", "province": "ชลบุรี"}, {"name": "B", "province": "ชลบุรี"}])
            self.assertEqual(audit_v1_files([p]).files[0].provinces["ชลบุรี"], 2)

    def test_07_category_coverage_is_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A", "category": "Eat, Vegetarian"}])
            f = audit_v1_files([p]).files[0]
            self.assertEqual(f.categories["eat"], 1)
            self.assertEqual(f.categories["vegetarian"], 1)

    def test_08_invalid_reasons_are_aggregated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"foo": "bar"}, {"lat": 1}])
            f = audit_v1_files([p]).files[0]
            self.assertEqual(f.invalid_reasons["missing place name"], 2)

    def test_09_unsupported_json_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "metadata_index.json", {"meta": {"x": 1}})
            r = audit_v1_files([p])
            self.assertIn(str(p), r.unreadable_files)

    def test_10_duplicate_candidate_keys_across_files_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.write_json(tmp, "eat_index.json", [{"id": "1", "name": "Same", "lat": 13, "lng": 101, "province": "X"}])
            b = self.write_json(tmp, "veg_index.json", [{"id": "2", "name": "Same", "lat": 13, "lng": 101, "province": "X"}])
            r = audit_v1_files([a, b])
            self.assertEqual(len(r.duplicate_candidate_groups), 1)
            self.assertEqual(r.duplicate_candidate_groups[0].occurrences, 2)

    def test_11_distinct_places_are_not_duplicate_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.write_json(tmp, "eat_index.json", [{"name": "A", "lat": 13, "lng": 101}])
            b = self.write_json(tmp, "veg_index.json", [{"name": "B", "lat": 14, "lng": 100}])
            self.assertEqual(len(audit_v1_files([a, b]).duplicate_candidate_groups), 0)

    def test_12_report_is_machine_serializable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A"}])
            payload = audit_v1_files([p]).to_dict()
            json.dumps(payload, ensure_ascii=False)
            self.assertEqual(payload["mode"], "dry-run-read-only")

    def test_13_discovery_only_selects_index_named_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = self.write_json(tmp, "vegetarian_index.json", [])
            self.write_json(tmp, "config.json", [])
            self.assertEqual(discover_v1_place_json(tmp), (idx,))

    def test_14_discovery_excludes_v2_and_test_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_json(tmp, "tests_v2/fake_index.json", [])
            self.write_json(tmp, "place_platform_v2/fake_index.json", [])
            real = self.write_json(tmp, "real_index.json", [])
            self.assertEqual(discover_v1_place_json(tmp), (real,))

    def test_15_audit_never_creates_database_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(tmp, "places_index.json", [{"name": "A"}])
            audit_v1_files([p])
            self.assertFalse(any(x.suffix in {".db", ".sqlite", ".sqlite3"} for x in Path(tmp).iterdir()))

    def test_16_empty_input_is_valid_audit(self):
        r = audit_v1_files([])
        self.assertEqual(r.total_records, 0)
        self.assertEqual(r.to_dict()["summary"]["files_audited"], 0)

    def test_17_auto_discovery_ignores_nested_history_and_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.write_json(tmp, "vegetarian_index.json", [])
            self.write_json(tmp, "backups/vegetarian_index_old.json", [])
            self.write_json(tmp, "data/archive/go_index.json", [])
            self.write_json(tmp, "data/candidates/service_index.json", [])
            self.assertEqual(discover_v1_place_json(tmp), (root,))

    def test_18_audit_reports_actual_top_level_keys_for_mapping_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.write_json(
                tmp,
                "vegetarian_index.json",
                [
                    {"name": "A", "province_th": "ชลบุรี", "diet_type": "vegetarian"},
                    {"name": "B", "province_th": "ระยอง", "diet_type": "vegan"},
                ],
            )
            f = audit_v1_files([p]).files[0]
            self.assertEqual(f.top_level_keys["province_th"], 2)
            self.assertEqual(f.top_level_keys["diet_type"], 2)


if __name__ == "__main__":
    unittest.main()
