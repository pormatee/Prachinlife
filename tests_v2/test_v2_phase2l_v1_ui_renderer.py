
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

APP = Path("app.js")
BASE = "5be9a3d"


class TestPhase2LV1UIRenderer(unittest.TestCase):
    def test_l01_v2_bridge_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("PrachinLifeV2Runtime", text)
        self.assertIn("getPreferredPlaceDataset", text)

    def test_l02_v2_search_nearme_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("searchPrachinLifeV2Places", text)
        self.assertIn("getPrachinLifeV2NearMe", text)

    def test_l03_internal_beta_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("PrachinLifeV2Beta", text)

    def test_l04_app_syntax_has_render_functions(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("renderEat", text)


if __name__ == "__main__":
    unittest.main()
