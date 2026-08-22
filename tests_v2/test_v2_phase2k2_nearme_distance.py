
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path("app.js")


class TestPhase2K2NearMeDistance(unittest.TestCase):
    def test_k21_user_location_supports_both_shapes(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("userPoint.latitude ?? userPoint.lat", text)
        self.assertIn("userPoint.longitude ?? userPoint.lng", text)

    def test_k22_distance_aliases_present(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "distance:",
            "distance_km:",
            "distanceKm:",
            "computedDistance:",
        ):
            self.assertIn(marker, text)

    def test_k23_distance_text_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("distance_text:", text)
        self.assertIn("กม.", text)

    def test_k24_nearme_still_uses_calculator(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("calculatePlaceDistance(", text)


if __name__ == "__main__":
    unittest.main()
