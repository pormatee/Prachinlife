
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path("app.js")


class TestPhase2ECategoryBridge(unittest.TestCase):
    def test_e01_category_bridge_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("getPreferredPlaceDataset", text)
        self.assertIn("getPrachinLifeV2Places", text)

    def test_e02_supported_categories_present(self):
        text = APP.read_text(encoding="utf-8")
        for category in ("eat", "vegetarian", "go", "service"):
            self.assertIn(f'"{category}"', text)

    def test_e03_v1_fallback_is_explicit(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("fallbackDataset", text)
        self.assertIn("return fallbackDataset", text)

    def test_e04_v2_requires_ready_status(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('getStatus() !== "ready"', text)

    def test_e05_empty_v2_category_falls_back(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("if (!v2Places.length)", text)


if __name__ == "__main__":
    unittest.main()
