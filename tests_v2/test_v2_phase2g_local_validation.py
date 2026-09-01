
from __future__ import annotations

import json
import unittest
from pathlib import Path

EXPORT = Path("data/v2/exports/decision_published_places_v1.json")
APP = Path("app.js")
INDEX = Path("index.html")
ADAPTER = Path("js/core/v2-place-adapter.js")


class TestPhase2GLocalValidation(unittest.TestCase):
    def test_g01_export_contract_and_count(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "prachinlife-published-projection-web-1")
        self.assertEqual(payload["authority"], "decision_published_places_v1")
        self.assertEqual(payload["count"], len(payload["places"]))
        self.assertGreater(payload["count"], 0)

    def test_g02_all_export_places_have_geo(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        for place in payload["places"]:
            lat = place["latitude"]
            lon = place["longitude"]
            self.assertEqual(lat is None, lon is None)
            if lat is not None:
                self.assertIsInstance(lat, (int, float))
                self.assertIsInstance(lon, (int, float))

    def test_g03_frontend_v2_bridge_present(self):
        app = APP.read_text(encoding="utf-8")
        self.assertIn("PrachinLifeV2Runtime", app)
        self.assertIn("getPreferredPlaceDataset", app)
        self.assertIn("searchPrachinLifeV2Places", app)
        self.assertIn("getPrachinLifeV2NearMe", app)

    def test_g04_index_loads_adapter(self):
        index = INDEX.read_text(encoding="utf-8")
        self.assertIn("js/core/v2-place-adapter.js", index)

    def test_g05_adapter_loads_v2_export(self):
        adapter = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("decision_published_places_v1.json", adapter)
        self.assertIn("loadV2Places", adapter)


if __name__ == "__main__":
    unittest.main()
