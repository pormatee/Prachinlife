
from __future__ import annotations
import unittest
from pathlib import Path

APP = Path("app.js")
STYLE = Path("style.css")
INDEX = Path("index.html")

class TestPhase2PFinalEatCardParity(unittest.TestCase):
    def test_p01_exact_shared_markup_structure(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            'promotion-card eat-card eat-v1-card',
            'promotion-image-wrap eat-image-wrap',
            'source-pill',
            'promotion-body',
            'promotion-meta',
            'promotion-title',
            'promotion-description',
            'placeCard.renderActions',
            'source-button',
        ):
            self.assertIn(marker, text)

    def test_p02_nearme_distance_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("place?._distance", text)
        self.assertIn("formatDistance", text)
        self.assertIn("จากตำแหน่งของคุณ", text)

    def test_p03_v2_and_v1_geo_supported(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("place?.location?.latitude", text)
        self.assertIn("?? place?.latitude", text)
        self.assertIn("?? place?.lat", text)

    def test_p04_v2_datasource_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("getEatDatasetV2First", text)
        self.assertIn("PrachinLifeV2Runtime", text)

    def test_p05_experimental_phase2n_css_absent(self):
        text = STYLE.read_text(encoding="utf-8")
        self.assertNotIn("PRACHINLIFE UNIFIED PLACE CARD V2N1", text)
        self.assertNotIn("PRACHINLIFE V2 / FINAL PLACE CARD UI", text)

    def test_p06_cache_bust_present(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("style.css?v=phase10p1-20260823", text)

if __name__ == "__main__":
    unittest.main()
