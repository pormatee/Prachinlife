import sqlite3
import unittest
from pathlib import Path
from place_platform_v2.web_export import _canonical_url_key, _links_for_place

ROOT=Path(__file__).resolve().parents[1]

class TestPhase2Y5AdditionalSourcePriority(unittest.TestCase):
    def test_y501_export_deduplicates_equivalent_urls(self):
        con=sqlite3.connect(":memory:"); con.row_factory=sqlite3.Row
        con.execute("CREATE TABLE place_evidence (place_id TEXT,source_name TEXT,source_record_id TEXT,source_url TEXT,status TEXT,observed_at TEXT,evidence_id TEXT)")
        con.executemany("INSERT INTO place_evidence VALUES (?,?,?,?,?,?,?)",[
          ("p","Wongnai","1","https://www.wongnai.com/restaurants/abc/","supported","2026-08-22","1"),
          ("p","Wongnai","2","https://www.wongnai.com/restaurants/abc","verified","2026-08-22","2")])
        links=_links_for_place(con,"p")
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]["type"],"wongnai")

    def test_y502_url_key_ignores_fragment_and_trailing_slash(self):
        self.assertEqual(
          _canonical_url_key("https://Example.com/place/#reviews"),
          _canonical_url_key("https://example.com/place"))

    def test_y503_card_priority_matches_product_policy(self):
        text=(ROOT/"js/core/place-card.js").read_text(encoding="utf-8")
        self.assertIn("google_maps: 2, wongnai: 3, facebook: 4, web: 5",text)
        self.assertIn("canonicalUrlKey",text)

    def test_y504_public_asset_cache_busted(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("place-card.js?v=phase10-20260823",html)

if __name__=="__main__": unittest.main()
