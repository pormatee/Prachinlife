from __future__ import annotations

import json
import unittest
from pathlib import Path

EXPORT = Path("data/v2/exports/decision_published_places_v1.json")
ADAPTER = Path("js/core/v2-place-adapter.js")
INDEX = Path("index.html")
APP = Path("app.js")


class TestV2FrontendBridge(unittest.TestCase):
    def test_d01_export_contract(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "prachinlife-published-projection-web-1")
        self.assertEqual(payload["authority"], "decision_published_places_v1")
        self.assertEqual(payload["count"], len(payload["places"]))

    def test_d02_adapter_exists(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("loadV2Places", text)
        self.assertIn("toLegacyPlace", text)
        self.assertIn("decision_published_places_v1.json", text)

    def test_d03_index_load_order(self):
        text = INDEX.read_text(encoding="utf-8")
        adapter = text.find("js/core/v2-place-adapter.js")
        app = text.find("app.js")
        self.assertGreaterEqual(adapter, 0)
        self.assertGreaterEqual(app, 0)
        self.assertLess(adapter, app)

    def test_d04_app_has_v2_bridge_and_fallback(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("loadPrachinLifeV2Data", text)
        self.assertIn("fallback_v1", text)
        self.assertIn("PrachinLifeV2Runtime", text)


if __name__ == "__main__":
    unittest.main()
