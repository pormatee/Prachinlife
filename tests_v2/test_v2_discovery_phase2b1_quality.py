from __future__ import annotations
import unittest
from place_platform_v2.osm_quality import (
    GridBox, build_area_bbox_query, build_grid, dedupe_elements,
)

class TestPhase2B1Quality(unittest.TestCase):
    def test_q01_grid_4x4(self):
        self.assertEqual(len(build_grid(0,0,4,4,4,4)), 16)

    def test_q02_area_and_bbox_combined(self):
        q = build_area_bbox_query("TH-25", GridBox(1,2,3,4))
        self.assertIn('["ISO3166-2"="TH-25"]', q)
        self.assertIn("(area.searchArea)(1,2,3,4)", q)

    def test_q03_all_category_families_present(self):
        q = build_area_bbox_query("TH-25", GridBox(1,2,3,4))
        for marker in ("restaurant", 'nwr["shop"]', 'nwr["tourism"]', 'nwr["healthcare"]'):
            self.assertIn(marker, q)

    def test_q04_blank_iso_rejected(self):
        with self.assertRaises(ValueError):
            build_area_bbox_query(" ", GridBox(1,2,3,4))

    def test_q05_dedupe_stable(self):
        result = dedupe_elements([
            {"type":"node","id":2},
            {"type":"node","id":1},
            {"type":"node","id":2},
        ])
        self.assertEqual(
            [(x["type"], x["id"]) for x in result],
            [("node",1),("node",2)],
        )

if __name__ == "__main__":
    unittest.main()
