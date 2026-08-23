import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.js').read_text(encoding='utf-8')

class RecommendedDiversityTest(unittest.TestCase):
    def test_recommended_dedupes_same_identity(self):
        self.assertIn('const seenRecommendedPlaces = new Set();', APP)
        self.assertIn('seenRecommendedPlaces.has(key)', APP)
        self.assertIn('seenRecommendedPlaces.add(key)', APP)

    def test_identity_keeps_content_type_and_category(self):
        self.assertIn('return `${contentType}|${category}|${title}`;', APP)

    def test_station_suffixes_are_normalized_for_recommendations(self):
        self.assertRegex(APP, r'service\\s\+station|service\\s\+station')
        self.assertIn('ปั๊มน้ำมัน|ปั้มน้ำมัน|ปั๊ม|ปั้ม', APP)

    def test_dedupe_is_recommendation_only(self):
        # Do not mutate source service arrays or DB/export data here.
        segment = APP[APP.index('function renderRecommended('):APP.index('function renderRecommendedDealRail()')]
        self.assertNotIn('allServicePlaces =', segment)
        self.assertNotIn('primaryServicePlaces =', segment)

if __name__ == '__main__':
    unittest.main()
