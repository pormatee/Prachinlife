import sqlite3
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.web_export import _links_for_place, export_prachinlife_json


class TestPhase2Y3TrustedLinksVip(unittest.TestCase):
    def test_y301_public_links_only_use_supported_or_verified_evidence(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE place_evidence (place_id TEXT, source_name TEXT, source_record_id TEXT, source_url TEXT, status TEXT, observed_at TEXT, evidence_id TEXT)")
        rows = [
            ("p", "Candidate", "c", "https://candidate.example/x", "candidate", "2026-08-22", "1"),
            ("p", "Supported", "s", "https://supported.example/x", "supported", "2026-08-22", "2"),
            ("p", "Verified", "v", "https://verified.example/x", "verified", "2026-08-22", "3"),
            ("p", "Stale", "t", "https://stale.example/x", "stale", "2026-08-22", "4"),
        ]
        con.executemany("INSERT INTO place_evidence VALUES (?,?,?,?,?,?,?)", rows)
        urls = [x["url"] for x in _links_for_place(con, "p")]
        self.assertEqual(urls, ["https://supported.example/x", "https://verified.example/x"])

    def test_y302_vip_page_is_exported_only_after_non_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.sqlite3"
            out = Path(td) / "out.json"
            con = sqlite3.connect(db)
            con.executescript("""
              CREATE TABLE places (place_id TEXT, canonical_name TEXT, latitude REAL, longitude REAL, address_text TEXT, province TEXT, categories_json TEXT, phone TEXT, website TEXT, lifecycle TEXT);
              CREATE TABLE place_evidence (place_id TEXT, source_name TEXT, source_record_id TEXT, source_url TEXT, field_name TEXT, value_json TEXT, status TEXT, observed_at TEXT, evidence_id TEXT);
            """)
            con.execute("INSERT INTO places VALUES (?,?,?,?,?,?,?,?,?,?)", ("p","ร้านทดสอบ",14.0,101.0,"","ปราจีนบุรี",'["restaurant"]',None,None,"active"))
            con.execute("INSERT INTO place_evidence VALUES (?,?,?,?,?,?,?,?,?)", ("p","admin","1",None,"prachinlife_page_url",'"/places/p"',"supported","2026-08-22","e1"))
            con.commit(); con.close()
            payload = export_prachinlife_json(db, out)
            self.assertEqual(payload["places"][0]["prachinlife_page_url"], "/places/p")

    def test_y303_card_prefers_vip_before_external_sources(self):
        text = Path("js/core/place-card.js").read_text(encoding="utf-8")
        self.assertIn('type: "prachinlife_vip"', text)
        self.assertIn('return getAdditionalLinks(place)[0] || null', text)


if __name__ == "__main__":
    unittest.main()
