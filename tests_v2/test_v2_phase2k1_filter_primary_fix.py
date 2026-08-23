
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path("app.js")
ADAPTER = Path("js/core/v2-place-adapter.js")


class TestPhase2K1(unittest.TestCase):
    def test_k11_vegetarian_prefers_primary_fallback(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("primaryVegetarianPlaces", text)
        self.assertIn("getVegetarianDatasetV2First", text)

    def test_k12_eat_category_uses_primary_type(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn(
            'group === "eat" || group === "service"',
            text,
        )

    def test_k13_legacy_eat_aliases_present(self):
        text = ADAPTER.read_text(encoding="utf-8")
        for marker in (
            "eat_type:",
            "food_type:",
            "place_type:",
            "content_type:",
            "subtype:",
        ):
            self.assertIn(marker, text)

    def test_k14_main_category_stays_group(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("main_category: group", text)


if __name__ == "__main__":
    unittest.main()
