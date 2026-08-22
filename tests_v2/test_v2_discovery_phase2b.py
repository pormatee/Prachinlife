from __future__ import annotations
import unittest
from place_platform_v2.osm_live import (
    OSMFetchReport,
    build_province_place_query,
    dedupe_elements,
)

class TestDiscoveryPhase2B(unittest.TestCase):
    def test_phase2b_01_query_requires_iso(self):
        with self.assertRaises(ValueError):
            build_province_place_query("  ")

    def test_phase2b_02_query_is_province_scoped(self):
        query = build_province_place_query("TH-25")
        self.assertIn('["ISO3166-2"="TH-25"]', query)

    def test_phase2b_03_query_includes_eat(self):
        query = build_province_place_query("TH-25")
        self.assertIn("restaurant", query)
        self.assertIn("cafe", query)

    def test_phase2b_04_query_includes_shopping(self):
        self.assertIn('nwr["shop"]', build_province_place_query("TH-25"))

    def test_phase2b_05_query_includes_travel(self):
        self.assertIn('nwr["tourism"]', build_province_place_query("TH-25"))

    def test_phase2b_06_query_includes_services(self):
        query = build_province_place_query("TH-25")
        self.assertIn('nwr["healthcare"]', query)
        self.assertIn("hospital", query)

    def test_phase2b_07_dedupe_is_stable(self):
        raw = [
            {"type": "node", "id": 2},
            {"type": "node", "id": 1},
            {"type": "node", "id": 2},
        ]
        result = dedupe_elements(raw)
        self.assertEqual(
            [(x["type"], x["id"]) for x in result],
            [("node", 1), ("node", 2)],
        )

    def test_phase2b_08_fetch_report_contract(self):
        report = OSMFetchReport(
            elements=({"type": "node", "id": 1},),
            endpoint="https://example.invalid",
            attempts=1,
            coverage_complete=True,
        )
        self.assertEqual(len(report.elements), 1)
        self.assertTrue(report.coverage_complete)

if __name__ == "__main__":
    unittest.main()
