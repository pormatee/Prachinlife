
from __future__ import annotations

import unittest
from pathlib import Path

INDEX = Path("index.html")
APP = Path("app.js")


class TestPhase2P1AppCache(unittest.TestCase):
    def test_p11_app_cache_busted(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn(
            "app.js?v=",
            text,
        )

    def test_p12_adapter_cache_busted(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn(
            "js/core/v2-place-adapter.js?v=phase2y2-20260822",
            text,
        )

    def test_p13_new_eat_renderer_is_in_app(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn(
            'promotion-card eat-card eat-v1-card',
            text,
        )
        self.assertIn(
            "จากตำแหน่งของคุณ",
            text,
        )
        self.assertIn(
            "placeCard.renderActions",
            text,
        )


if __name__ == "__main__":
    unittest.main()
