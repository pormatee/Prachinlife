
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path("app.js")


class TestPhase2MLatestUIExactDistance(unittest.TestCase):
    def test_m01_distance_supports_nested_location(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("place?.location?.latitude", text)
        self.assertIn("place?.location?.longitude", text)

    def test_m02_distance_supports_v2_flat_coordinates(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("?? place?.latitude", text)
        self.assertIn("?? place?.longitude", text)
        self.assertIn("?? place?.lat", text)
        self.assertIn("?? place?.lng", text)

    def test_m03_renderer_uses_distance(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("place?._distance", text)
        self.assertIn("formatDistance", text)

    def test_m04_v2_bridge_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("PrachinLifeV2Runtime", text)
        self.assertIn("getEatDatasetV2First", text)


if __name__ == "__main__":
    unittest.main()
