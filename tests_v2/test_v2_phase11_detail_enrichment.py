import json, shutil, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.phase11_detail_enrichment import collect_claims,persist_claims
from place_platform_v2.web_export import export_prachinlife_json
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/v2/place_platform_v2.sqlite3'; EXP=ROOT/'data/v2/exports/prachinlife_places_v2.json'; RAW=ROOT/'data/v2/discovery_reports/osm_th25_grid_latest.json'
class Phase11DetailEnrichmentTest(unittest.TestCase):
 def test_1101_collect_only_identity_anchored_osm(self):
  claims,meta=collect_claims(DB,EXP,RAW); self.assertEqual(meta['published_places'],220); self.assertEqual(meta['matched_osm_identity'],20); self.assertFalse(meta['raw_coverage_complete']); self.assertGreater(len(claims),0)
 def test_1102_expected_real_claims_present(self):
  claims,_=collect_claims(DB,EXP,RAW); vals={(c.field_name,c.value) for c in claims}; self.assertIn(('opening_hours','08:00-20:00'),vals); self.assertIn(('opening_hours','24/7'),vals); self.assertIn(('district','ประจันตคาม'),vals); self.assertIn(('subdistrict','โพธิ์งาม'),vals)
 def test_1103_no_real_image_without_direct_url(self):
  claims,_=collect_claims(DB,EXP,RAW); self.assertFalse(any(c.field_name=='real_image' for c in claims))
 def test_1104_evidence_only_no_canonical_mutation(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; shutil.copy2(DB,db); con=sqlite3.connect(db); before=con.execute('select * from places order by place_id').fetchall(); con.close(); claims,_=collect_claims(db,EXP,RAW); persist_claims(db,claims); con=sqlite3.connect(db); after=con.execute('select * from places order by place_id').fetchall(); statuses={r[0] for r in con.execute("select distinct status from place_evidence where metadata_json like '%phase11-detail-enrichment-v1%'")}; con.close(); self.assertEqual(before,after); self.assertEqual(statuses,{'supported'})
 def test_1105_candidate_details_stay_unpublished(self):
  from place_platform_v2.web_export import _detail_evidence_for_place
  con=sqlite3.connect(':memory:'); con.row_factory=sqlite3.Row; con.execute('create table place_evidence(field_name text,value_json text,status text,observed_at text,source_type text,source_name text,source_url text,source_record_id text,evidence_id text,place_id text)'); con.execute("insert into place_evidence values ('description','\"guess\"','candidate','1','web','x','https://x.example',null,'1','p')"); self.assertEqual(_detail_evidence_for_place(con,'p'),{})
 def test_1106_export_increases_coverage_with_provenance(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; out=Path(td)/'out.json'; shutil.copy2(DB,db); claims,_=collect_claims(db,EXP,RAW); persist_claims(db,claims); payload=export_prachinlife_json(db,out); by={p['name']:p for p in payload['places']}; platoo=by['The Platoo Kitchen']; self.assertEqual(platoo['opening_hours'],'08:00-20:00'); self.assertEqual(platoo['phone'],'+66868416818'); self.assertEqual(platoo['detail_provenance']['opening_hours']['status'],'supported'); khun=by['ขุนเขาคาเฟ่']; self.assertEqual(khun['district'],'ประจันตคาม'); self.assertIn('121',khun['address'])
 def test_1107_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'
   shutil.copy2(DB,db)
   con=sqlite3.connect(db)
   con.execute(
    "delete from place_evidence "
    "where metadata_json like '%phase11-detail-enrichment-v1%'"
   )
   con.commit()
   con.close()
   claims,_=collect_claims(db,EXP,RAW)
   a=persist_claims(db,claims)
   b=persist_claims(db,claims)
   self.assertGreater(a,0)
   self.assertEqual(b,0)
if __name__=='__main__': unittest.main()
