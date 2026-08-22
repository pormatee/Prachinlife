
from __future__ import annotations

import json
import unittest
from pathlib import Path

REPORT = Path("data/v2/discovery_reports/phase2h_comparative_beta_ready.json")


class TestPhase2HComparative(unittest.TestCase):
    def test_h01_report_exists(self):
        self.assertTrue(REPORT.exists())

    def test_h02_required_categories_present(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        for category in ("eat", "vegetarian", "go", "service"):
            self.assertIn(category, report["v2_counts"])

    def test_h03_v2_core_categories_nonempty(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertGreater(report["v2_counts"]["eat"], 0)
        self.assertGreater(report["v2_counts"]["go"], 0)
        self.assertGreater(report["v2_counts"]["service"], 0)

    def test_h04_beta_readiness_is_explicit(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertIn("beta_ready", report)
        self.assertIn("production_switch", report)


if __name__ == "__main__":
    unittest.main()
