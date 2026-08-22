
from __future__ import annotations

import json
import unittest
from pathlib import Path

EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")
APP = Path("app.js")
INDEX = Path("index.html")
ADAPTER = Path("js/core/v2-place-adapter.js")


class TestPhase2GLocalValidation(unittest.TestCase):
    def test_g01_export_contract_and_count(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "prachinlife-v2-json-1")
        self.assertEqual(payload["count"], len(payload["places"]))
        self.assertGreater(payload["count"], 0)

    def test_g02_all_export_places_have_geo(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        for place in payload["places"]:
            self.assertIsNotNone(place["latitude"])
            self.assertIsNotNone(place["longitude"])

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
        self.assertIn("prachinlife_places_v2.json", adapter)
        self.assertIn("loadV2Places", adapter)


if __name__ == "__main__":
    unittest.main()
