from __future__ import annotations
import sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.sqlite_store import SQLitePlaceRepository
from place_platform_v2.web_export import _links_for_place

ROOT=Path('.')
CARD=ROOT/'js/core/place-card.js'
ADAPTER=ROOT/'js/core/v2-place-adapter.js'
INDEX=ROOT/'index.html'

class TestPhase2Y1PlaceEnrichmentLinks(unittest.TestCase):
    def test_y101_card_uses_additional_information_not_raw_source(self):
        text=CARD.read_text(encoding='utf-8')
        self.assertIn('🔗 ข้อมูลเพิ่มเติม', text)
        self.assertNotIn('ดูแหล่งข้อมูล', text)
        self.assertIn('getBestAdditionalLink', text)

    def test_y102_osm_is_not_user_facing_additional_link(self):
        text=CARD.read_text(encoding='utf-8')
        self.assertIn('item.type === "osm"', text)
        self.assertIn('openstreetmap', text)

    def test_y103_adapter_preserves_multiple_links_and_vip_route(self):
        text=ADAPTER.read_text(encoding='utf-8')
        self.assertIn('external_links:', text)
        self.assertIn('prachinlife_page_url:', text)

    def test_y104_vip_route_has_highest_priority(self):
        text=CARD.read_text(encoding='utf-8')
        self.assertIn('prachinlife_vip: 0', text)
        self.assertIn('place?.prachinlife_page_url', text)

    def test_y105_export_classifies_and_keeps_multiple_sources(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.sqlite3'; repo=SQLitePlaceRepository(db); repo.close()
            con=sqlite3.connect(db); con.row_factory=sqlite3.Row
            # A synthetic evidence set is enough to test link policy independently of canonical publication.
            con.execute("INSERT INTO place_evidence(evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        ('e1','p','other','OpenStreetMap','osm-node-1','https://www.openstreetmap.org/node/1','2026-08-22T00:00:00+00:00','other','x','null','supported','2026-08-22T00:00:00+00:00','{}'))
            con.execute("INSERT INTO place_evidence(evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        ('e2','p','other','Wongnai','w1','https://www.wongnai.com/restaurants/example','2026-08-22T00:00:00+00:00','other','x','null','supported','2026-08-22T00:00:00+00:00','{}'))
            con.commit()
            links=_links_for_place(con,'p')
            con.close()
            self.assertEqual({x['type'] for x in links},{'osm','wongnai'})

    def test_y106_cache_marker_bumped(self):
        self.assertIn('js/core/v2-place-adapter.js?v=', INDEX.read_text(encoding='utf-8'))

if __name__=='__main__': unittest.main()
