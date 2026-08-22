from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path('.')
INDEX = ROOT / 'index.html'
DETAIL = ROOT / 'js/core/place-detail.js'
APP = ROOT / 'app.js'
VEG = ROOT / 'js/modules/vegetarian.js'
GO = ROOT / 'js/modules/go.js'
SERVICE = ROOT / 'js/modules/service.js'


class TestPhase2S2UnifiedDetailRendering(unittest.TestCase):
    def test_s201_detail_contract_loaded_before_place_renderers(self):
        text = INDEX.read_text(encoding='utf-8')
        detail = text.index('js/core/place-detail.js')
        for marker in ('js/modules/vegetarian.js', 'js/modules/go.js', 'js/modules/service.js', 'app.js'):
            self.assertLess(detail, text.index(marker))

    def test_s202_all_place_renderers_use_detail_contract(self):
        texts = [
            APP.read_text(encoding='utf-8'),
            VEG.read_text(encoding='utf-8'),
            GO.read_text(encoding='utf-8'),
            SERVICE.read_text(encoding='utf-8'),
        ]
        for text in texts:
            self.assertIn('placeDetail.getDetail(', text)
            self.assertIn('placeDetail.renderFacts(', text)
            self.assertIn('placeCard.renderActions(place)', text)
            self.assertIn('placeCard.renderDataNote(place)', text)

    def test_s203_detail_contract_is_single_source_for_opening_hours(self):
        text = DETAIL.read_text(encoding='utf-8')
        self.assertIn('function getOpeningHours(', text)
        self.assertIn('meta.opening_hours', text)
        self.assertIn('place?.opening_hours', text)
        self.assertIn('place?.hours', text)

    def test_s204_detail_contract_renders_optional_description_only(self):
        text = DETAIL.read_text(encoding='utf-8')
        self.assertIn('if (detail.description)', text)
        self.assertNotIn('ไม่ระบุคำอธิบาย', text)
        self.assertNotIn('ไม่มีรายละเอียด', text)

    def test_s205_local_and_nationwide_fallbacks_are_explicit(self):
        app = APP.read_text(encoding='utf-8')
        veg = VEG.read_text(encoding='utf-8')
        go = GO.read_text(encoding='utf-8')
        service = SERVICE.read_text(encoding='utf-8')
        self.assertRegex(app, r'placeDetail\.renderFacts\(\s*place,\s*"ปราจีนบุรี"')
        self.assertRegex(go, r'placeDetail\.renderFacts\(\s*place,\s*"ปราจีนบุรี"')
        self.assertRegex(service, r'placeDetail\.renderFacts\(\s*place,\s*"ปราจีนบุรี"')
        self.assertRegex(veg, r'placeDetail\.renderFacts\(\s*place\s*\)')

    def test_s206_no_public_production_switch(self):
        combined = '\n'.join(p.read_text(encoding='utf-8') for p in (DETAIL, APP, VEG, GO, SERVICE))
        self.assertNotIn('public_production = true', combined)
        self.assertNotIn('publicProduction = true', combined)
        self.assertIn('getEatDatasetV2First', APP.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
