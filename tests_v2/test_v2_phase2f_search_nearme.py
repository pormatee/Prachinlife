
from __future__ import annotations

import json
import unittest
from pathlib import Path

APP = Path("app.js")
EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")


class TestPhase2FSearchNearMe(unittest.TestCase):
    def test_f01_v2_export_has_coordinates(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertGreater(payload["count"], 0)
        for place in payload["places"]:
            self.assertIsNotNone(place["latitude"])
            self.assertIsNotNone(place["longitude"])

    def test_f02_v2_search_helper_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("searchPrachinLifeV2Places", text)

    def test_f03_v2_nearme_helper_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("getPrachinLifeV2NearMe", text)

    def test_f04_search_uses_v2_runtime_dataset(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("getPrachinLifeV2Places()", text)

    def test_f05_nearme_uses_distance_function(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("calculatePlaceDistance", text)


if __name__ == "__main__":
    unittest.main()
