from __future__ import annotations
import unittest

from place_platform_v2.osm_grid import (
    GridBox, build_bbox_query, build_grid, dedupe_elements,
)

class TestDiscoveryPhase2BGrid(unittest.TestCase):
    def test_grid_01_builds_requested_cells(self):
        self.assertEqual(len(build_grid(0, 0, 3, 3, 3, 3)), 9)

    def test_grid_02_invalid_bbox_rejected(self):
        with self.assertRaises(ValueError):
            build_grid(1, 0, 0, 1)

    def test_grid_03_query_is_bbox_scoped(self):
        self.assertIn("(1,2,3,4)", build_bbox_query(GridBox(1, 2, 3, 4)))

    def test_grid_04_query_has_categories(self):
        q = build_bbox_query(GridBox(1, 2, 3, 4))
        self.assertIn('nwr["shop"]', q)
        self.assertIn('nwr["tourism"]', q)
        self.assertIn('nwr["healthcare"]', q)
        self.assertIn("restaurant", q)

    def test_grid_05_dedupe_across_boxes(self):
        result = dedupe_elements([
            {"type": "node", "id": 1},
            {"type": "node", "id": 1},
            {"type": "way", "id": 2},
        ])
        self.assertEqual(len(result), 2)

if __name__ == "__main__":
    unittest.main()
