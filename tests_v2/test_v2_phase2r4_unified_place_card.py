from __future__ import annotations

import json
import unittest
from pathlib import Path

from place_platform_v2.web_export import _source_link_from_record_id

ROOT = Path('.')
INDEX = ROOT / 'index.html'
STYLE = ROOT / 'style.css'
APP = ROOT / 'app.js'
CARD = ROOT / 'js/core/place-card.js'
ADAPTER = ROOT / 'js/core/v2-place-adapter.js'
EXPORT = ROOT / 'data/v2/exports/prachinlife_places_v2.json'
MODULES = [
    ROOT / 'js/modules/vegetarian.js',
    ROOT / 'js/modules/go.js',
    ROOT / 'js/modules/service.js',
]


class TestPhase2R4UnifiedPlaceCard(unittest.TestCase):
    def test_r401_shared_place_card_loaded_before_modules(self):
        text = INDEX.read_text(encoding='utf-8')
        card = text.index('js/core/place-card.js')
        for marker in ('js/modules/vegetarian.js', 'js/modules/go.js', 'js/modules/service.js', 'app.js'):
            self.assertLess(card, text.index(marker))

    def test_r402_unified_action_contract(self):
        text = CARD.read_text(encoding='utf-8')
        for marker in (
            '📍 เปิดแผนที่', '📞 โทร', '🌐 เว็บไซต์', '🔗 ข้อมูลเพิ่มเติม',
            'getPhoneHref', 'getWebsite', 'getSourceUrl', 'getMapUrl', 'getBestAdditionalLink',
        ):
            self.assertIn(marker, text)
        self.assertIn('if (phoneHref)', text)
        self.assertIn('if (website)', text)
        self.assertIn('if (additional)', text)

    def test_r403_all_place_renderers_use_shared_actions(self):
        self.assertIn('placeCard.renderActions(place)', APP.read_text(encoding='utf-8'))
        for module in MODULES:
            text = module.read_text(encoding='utf-8')
            self.assertIn('placeCard.renderActions(place)', text, str(module))
            self.assertIn('placeCard.renderDataNote(place)', text, str(module))

    def test_r404_user_facing_location_fallback(self):
        text = CARD.read_text(encoding='utf-8')
        for marker in ('place?.district', 'place?.area', 'place?.address', 'place?.province'):
            self.assertIn(marker, text)
        eat = APP.read_text(encoding='utf-8')
        self.assertIn('placeDetail.renderFacts(', eat)

    def test_r405_technical_source_name_hidden(self):
        text = CARD.read_text(encoding='utf-8')
        self.assertIn('TECHNICAL_SOURCE_NAMES', text)
        self.assertIn('"place_platform_v2"', text)
        self.assertIn('return "แหล่งข้อมูลสาธารณะ"', text)

    def test_r406_osm_source_reconstruction(self):
        self.assertEqual(
            _source_link_from_record_id('prachinlife_index.json#osm-node-8477554774'),
            'https://www.openstreetmap.org/node/8477554774',
        )
        self.assertEqual(
            _source_link_from_record_id('x#osm-way-123'),
            'https://www.openstreetmap.org/way/123',
        )
        self.assertIsNone(_source_link_from_record_id('unknown'))

    def test_r407_export_contains_user_source_links(self):
        payload = json.loads(EXPORT.read_text(encoding='utf-8'))
        self.assertEqual(payload['count'], 220)
        with_source = [p for p in payload['places'] if p.get('source_url')]
        self.assertGreaterEqual(len(with_source), 200)
        self.assertTrue(all(p.get('source_name') for p in with_source))

    def test_r408_adapter_preserves_source_metadata(self):
        text = ADAPTER.read_text(encoding='utf-8')
        self.assertIn('source_name: text(place.source_name)', text)
        self.assertIn('source_url: text(place.source_url)', text)

    def test_r409_compact_action_grid(self):
        text = STYLE.read_text(encoding='utf-8')
        self.assertIn('.place-card-actions', text)
        self.assertIn('repeat(2, minmax(0, 1fr))', text)
        self.assertIn('.place-card-action:only-child', text)
        self.assertIn('.place-card-action-source', text)

    def test_r410_runtime_safety_preserved(self):
        text = APP.read_text(encoding='utf-8')
        self.assertIn('getEatDatasetV2First', text)
        self.assertIn('PrachinLifeV2Runtime', text)
        index = INDEX.read_text(encoding='utf-8')
        self.assertIn('phase2y2-20260822', index)


if __name__ == '__main__':
    unittest.main()
