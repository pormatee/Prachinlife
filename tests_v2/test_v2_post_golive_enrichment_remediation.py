import json, tempfile, unittest
from pathlib import Path
from place_platform_v2.staged_overlay import build_overlay_staging

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/v2/place_platform_v2.sqlite3'

class TestPostGoLiveEnrichmentRemediation(unittest.TestCase):
    def test_overlay_carries_trusted_external_links(self):
        with tempfile.TemporaryDirectory() as td:
            build_overlay_staging(DB, ROOT, td, 'ปราจีนบุรี')
            rows=[]
            for fn in ('prachinlife_index.json','vegetarian_index.json','go_index.json','service_index.json'):
                rows.extend(json.loads((Path(td)/fn).read_text(encoding='utf-8')))
            enriched=[r for r in rows if r.get('external_links')]
            self.assertTrue(enriched)
            useful=[l for r in enriched for l in r['external_links'] if l.get('type') != 'osm']
            self.assertTrue(useful)
            self.assertTrue(any('wongnai.com' in l.get('url','') for l in useful))

    def test_overlay_does_not_publish_candidate_real_image(self):
        with tempfile.TemporaryDirectory() as td:
            build_overlay_staging(DB, ROOT, td, 'ปราจีนบุรี')
            rows=[]
            for fn in ('prachinlife_index.json','vegetarian_index.json','go_index.json','service_index.json'):
                rows.extend(json.loads((Path(td)/fn).read_text(encoding='utf-8')))
            self.assertFalse(any(r.get('real_image') for r in rows))

if __name__=='__main__': unittest.main()
