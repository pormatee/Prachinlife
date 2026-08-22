
from __future__ import annotations

import json
import unittest
from pathlib import Path

APP = Path("app.js")
CONFIG = Path("data/v2/exports/prachinlife_v2_runtime_config.json")


class TestPhase2IInternalBeta(unittest.TestCase):
    def test_i01_runtime_config_exists(self):
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(data["mode"], "internal_beta")
        self.assertTrue(data["v2_first"])
        self.assertTrue(data["v1_fallback"])

    def test_i02_app_has_internal_beta_switch(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("PrachinLifeV2Beta", text)
        self.assertIn("internal_beta", text)

    def test_i03_v1_fallback_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("fallback_v1", text)
        self.assertIn("return fallbackDataset", text)

    def test_i04_search_and_nearme_preserved(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("searchPrachinLifeV2Places", text)
        self.assertIn("getPrachinLifeV2NearMe", text)


if __name__ == "__main__":
    unittest.main()
