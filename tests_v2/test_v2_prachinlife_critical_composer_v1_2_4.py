from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "prachinburi/index.html"
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"

class TestPrachinLifeCriticalComposerV124(unittest.TestCase):
    def test_01_production_root_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_critical_mobile_fix_is_inline(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="prachinlife-ai-critical-mobile-v12r4"', text)

    def test_03_panel_is_forced_full_viewport(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("#robotAssistPanel:not([hidden])", text)
        self.assertIn("position: fixed !important", text)
        self.assertIn("height: 100dvh !important", text)
        self.assertIn("z-index: 99999 !important", text)

    def test_04_composer_is_forced_to_viewport_bottom(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("#robotAssistPanel:not([hidden]) .robot-assist-composer", text)
        self.assertIn("bottom: 0 !important", text)
        self.assertIn("z-index: 100000 !important", text)

    def test_05_messages_scroll_inside_panel(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("overflow-y: auto !important", text)
        self.assertIn("padding-bottom: 104px !important", text)

    def test_06_preview_still_noindex(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex,nofollow"', text)

if __name__ == "__main__":
    unittest.main()
