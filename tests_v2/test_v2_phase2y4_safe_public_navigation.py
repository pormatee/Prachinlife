import sqlite3
import unittest
from pathlib import Path
from place_platform_v2.web_export import _links_for_place, _public_http_url

ROOT=Path(__file__).resolve().parents[1]

class TestPhase2Y4SafePublicNavigation(unittest.TestCase):
    def test_y401_export_rejects_unsafe_schemes(self):
        self.assertIsNone(_public_http_url('javascript:alert(1)'))
        self.assertIsNone(_public_http_url('data:text/html,x'))
        self.assertEqual(_public_http_url('example.com/x'),'https://example.com/x')

    def test_y402_links_drop_unsafe_supported_evidence(self):
        con=sqlite3.connect(':memory:'); con.row_factory=sqlite3.Row
        con.execute('CREATE TABLE place_evidence (place_id TEXT,source_name TEXT,source_record_id TEXT,source_url TEXT,status TEXT,observed_at TEXT,evidence_id TEXT)')
        con.executemany('INSERT INTO place_evidence VALUES (?,?,?,?,?,?,?)',[
          ('p','Bad','1','javascript:alert(1)','supported','2026-08-22','1'),
          ('p','Good','2','https://example.com/place','supported','2026-08-22','2')])
        self.assertEqual([x['url'] for x in _links_for_place(con,'p')],['https://example.com/place'])

    def test_y403_card_and_adapter_have_safe_url_guards(self):
        card=(ROOT/'js/core/place-card.js').read_text(encoding='utf-8')
        adapter=(ROOT/'js/core/v2-place-adapter.js').read_text(encoding='utf-8')
        for marker in ('safeHttpUrl','safeVipUrl'):
            self.assertIn(marker,card); self.assertIn(marker,adapter)
        self.assertIn('!url.startsWith("//")',card)
        self.assertIn('return safeHttpUrl(value)',card)

    def test_y404_public_assets_are_cache_busted(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('place-card.js?v=phase2y4-20260822',html)
        self.assertIn('v2-place-adapter.js?v=phase2y4-20260822',html)

if __name__=='__main__': unittest.main()
