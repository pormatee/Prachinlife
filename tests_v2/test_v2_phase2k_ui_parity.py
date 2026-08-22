
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path("app.js")
ADAPTER = Path("js/core/v2-place-adapter.js")


class TestPhase2KUIParity(unittest.TestCase):
    def test_k01_smart_fallback_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("coverageRatio", text)
        self.assertIn("coverageRatio < 0.80", text)
        self.assertIn("v2Places.length < 3", text)

    def test_k02_v1_fallback_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("return fallbackDataset", text)

    def test_k03_adapter_has_eat_filter_fields(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("eat_type", text)
        self.assertIn("food_type", text)
        self.assertIn("place_type", text)

    def test_k04_adapter_has_area_fallback(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("const displayArea", text)
        self.assertIn("province", text)

    def test_k05_adapter_has_maps_url(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("maps_url", text)
        self.assertIn("google.com/maps/search", text)


if __name__ == "__main__":
    unittest.main()
