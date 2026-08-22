from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.js').read_text(encoding='utf-8')

class TestNearMeCategoryReset(unittest.TestCase):
    def test_main_category_transition_resets_near_me_before_switch(self):
        m = re.search(r'function setMainCategory\([\s\S]*?\n}\n\n\nfunction updateMainCategoryButtons', APP)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertIn('resetNearMeForMainCategoryChange', body)
        self.assertLess(body.index('resetNearMeForMainCategoryChange'), body.index('currentMainCategory ='))

    def test_reset_clears_shared_location_and_all_nearme_buttons(self):
        m = re.search(r'function resetNearMeForMainCategoryChange\([\s\S]*?\n}\n\n\nfunction setMainCategory', APP)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertIn('userLocation = null', body)
        self.assertIn('updateNearMeState(false)', body)
        self.assertIn('updateServiceNearMeState(false)', body)
        self.assertIn('vegetarian.updateNearMeState', body)
        self.assertIn('goNearMeBtn.classList.remove', body)

    def test_same_category_does_not_reset_active_nearme(self):
        m = re.search(r'function resetNearMeForMainCategoryChange\([\s\S]*?\n}\n\n\nfunction setMainCategory', APP)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertRegex(body, r'nextCategory\s*===\s*currentMainCategory[\s\S]*?return;')

if __name__ == '__main__':
    unittest.main()
