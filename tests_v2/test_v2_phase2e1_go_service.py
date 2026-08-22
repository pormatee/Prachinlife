
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path("app.js")


class TestPhase2E1GoService(unittest.TestCase):
    def test_e11_go_helper_used(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("getGoDatasetV2First()", text)

    def test_e12_service_helper_used(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("getServiceDatasetV2First()", text)

    def test_e13_go_and_service_helpers_exist(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("function getGoDatasetV2First()", text)
        self.assertIn("function getServiceDatasetV2First()", text)

    def test_e14_v1_fallback_still_present(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("return fallbackDataset", text)


if __name__ == "__main__":
    unittest.main()
