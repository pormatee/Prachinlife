import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.web_export import export_prachinlife_json

ROOT=Path(__file__).resolve().parents[1]

class TestPhase2Y2PublicDetailEnrichment(unittest.TestCase):
    def test_y201_export_code_carries_enriched_detail_fields(self):
        text=(ROOT/'place_platform_v2/web_export.py').read_text(encoding='utf-8')
        for marker in ('_detail_evidence_for_place', '"opening_hours"', '"real_image"', '"description"', '"external_links"'):
            self.assertIn(marker,text)

    def test_y202_candidate_only_detail_is_not_published(self):
        text=(ROOT/'place_platform_v2/web_export.py').read_text(encoding='utf-8')
        self.assertIn('== "candidate"', text)

    def test_y203_adapter_preserves_public_enrichment(self):
        text=(ROOT/'js/core/v2-place-adapter.js').read_text(encoding='utf-8')
        for marker in ('real_image: text(place.real_image)', 'opening_hours: text(place.opening_hours)', 'description: text(place.description)', 'subdistrict: text(place.subdistrict)'):
            self.assertIn(marker,text)

    def test_y204_cache_bust(self):
        self.assertIn('v2-place-adapter.js?v=phase2y4-20260822',(ROOT/'index.html').read_text(encoding='utf-8'))

if __name__=='__main__': unittest.main()
