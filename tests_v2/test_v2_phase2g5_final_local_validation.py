
from __future__ import annotations

import json
import unittest
from pathlib import Path

EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")
APP = Path("app.js")
INDEX = Path("index.html")
ADAPTER = Path("js/core/v2-place-adapter.js")


class TestPhase2G5FinalLocalValidation(unittest.TestCase):
    def test_g51_export_contract(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "prachinlife-v2-json-1")
        self.assertEqual(payload["count"], len(payload["places"]))
        self.assertEqual(payload["count"], 220)

    def test_g52_categories_are_lists(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        for place in payload["places"]:
            self.assertIsInstance(place["categories"], list)

    def test_g53_frontend_bridges_present(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "PrachinLifeV2Runtime",
            "getPreferredPlaceDataset",
            "searchPrachinLifeV2Places",
            "getPrachinLifeV2NearMe",
        ):
            self.assertIn(marker, text)

    def test_g54_index_and_adapter_connected(self):
        index = INDEX.read_text(encoding="utf-8")
        adapter = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("js/core/v2-place-adapter.js", index)
        self.assertIn("prachinlife_places_v2.json", adapter)
        self.assertIn("CATEGORY_ALIASES", adapter)


if __name__ == "__main__":
    unittest.main()
