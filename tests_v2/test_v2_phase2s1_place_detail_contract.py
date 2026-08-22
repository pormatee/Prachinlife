from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
DETAIL=ROOT/'js/core/place-detail.js'
INDEX=ROOT/'index.html'
CARD=ROOT/'js/core/place-card.js'

class TestPhase2S1PlaceDetailContract(unittest.TestCase):
    def test_s101_detail_contract_exists(self):
        self.assertTrue(DETAIL.exists())
        text=DETAIL.read_text()
        for marker in ('getOpeningHours','getDescription','getDetail','renderFacts'):
            self.assertIn(marker,text)

    def test_s102_user_facing_fields(self):
        text=DETAIL.read_text()
        for marker in ('location','openingHours','phone','website','sourceName','sourceUrl','description','hasCoordinates'):
            self.assertIn(marker,text)

    def test_s103_no_invented_content(self):
        text=DETAIL.read_text()
        self.assertNotIn('เปิดทุกวัน', text)
        self.assertNotIn('08:00', text)
        self.assertNotIn('ยอดนิยม', text)

    def test_s104_loaded_after_card_before_modules(self):
        text=INDEX.read_text()
        card=text.index('js/core/place-card.js')
        detail=text.index('js/core/place-detail.js')
        veg=text.index('js/modules/vegetarian.js')
        self.assertLess(card,detail)
        self.assertLess(detail,veg)

    def test_s105_technical_source_hidden(self):
        text=CARD.read_text()
        self.assertIn('place_platform_v2',text)
        self.assertIn('แหล่งข้อมูลสาธารณะ',text)

if __name__=='__main__': unittest.main()
