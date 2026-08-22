from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.completeness import audit_places


EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")
DB = Path("data/v2/place_platform_v2.sqlite3")
SCRIPT = Path("scripts/audit_place_detail_completeness_v2.py")


class TestPhase2S3DataCompletenessAudit(unittest.TestCase):
    def test_s301_audit_counts_missing_fields_without_inference(self):
        report = audit_places([
            {"name": "A", "latitude": 1, "longitude": 2, "province": "X", "categories": ["cafe"]},
            {"name": "B", "latitude": 3, "longitude": 4, "province": "X", "categories": ["restaurant"], "phone": "123"},
        ])
        self.assertEqual(report["place_count"], 2)
        self.assertEqual(report["detail_fields"]["phone"]["present"], 1)
        self.assertEqual(report["detail_fields"]["opening_hours"]["present"], 0)

    def test_s302_real_image_supports_metadata_and_top_level(self):
        report = audit_places([
            {"image_url": "a.jpg"},
            {"metadata": {"photo_url": "b.jpg"}},
            {},
        ])
        self.assertEqual(report["detail_fields"]["real_image"]["present"], 2)
        self.assertEqual(report["detail_fields"]["real_image"]["missing"], 1)

    def test_s303_admin_priority_contains_expected_fields(self):
        report = audit_places([{}])
        fields = {item["field"] for item in report["admin_priority"]}
        self.assertTrue({"district", "area", "opening_hours", "phone", "website", "real_image", "description"}.issubset(fields))

    def test_s304_current_export_is_220_places(self):
        data = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertEqual(data.get("count"), 220)
        self.assertEqual(len(data.get("places", [])), 220)

    def test_s305_cli_is_read_only_for_central_db(self):
        before = DB.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--json", str(Path(tmp) / "audit.json"),
                    "--markdown", str(Path(tmp) / "audit.md"),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("RESULT=PASS", result.stdout)
        self.assertEqual(DB.read_bytes(), before)

    def test_s306_no_public_production_switch(self):
        combined = Path("place_platform_v2/completeness.py").read_text(encoding="utf-8") + SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("public_production", combined)
        self.assertNotIn("publicProduction", combined)


if __name__ == "__main__":
    unittest.main()
