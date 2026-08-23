from __future__ import annotations
import json, shutil, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.phase11_official_web_enrichment import collect_official_web_claims,persist_official_web_claims,POLICY
from place_platform_v2.web_export import export_prachinlife_json

DB=Path('data/v2/place_platform_v2.sqlite3')
MAN=Path('data/v2/discovery_reports/phase11_loop2_official_web_observations.json')

class Phase11OfficialWebEnrichmentTest(unittest.TestCase):
 def test_1121_manifest_collects_only_verified_official_claims(self):
  claims,meta=collect_official_web_claims(DB,MAN)
  self.assertEqual(meta['accepted_observations'],2); self.assertEqual(len(claims),7)
  self.assertEqual({c.field_name for c in claims},{'address','district','subdistrict','opening_hours','phone','website','description'})
 def test_1122_identity_mismatch_fails_closed(self):
  d=json.loads(MAN.read_text(encoding='utf-8')); d['observations'][0]['canonical_name']='wrong'
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'m.json'; p.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
   with self.assertRaises(ValueError): collect_official_web_claims(DB,p)
 def test_1123_untrusted_host_fails_closed(self):
  d=json.loads(MAN.read_text(encoding='utf-8')); d['observations'][0]['source_url']='https://example.com/x'
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'m.json'; p.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
   with self.assertRaises(ValueError): collect_official_web_claims(DB,p)
 def test_1124_persist_never_changes_canonical_places(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; shutil.copy2(DB,db); con=sqlite3.connect(db); before=con.execute('select count(*),sum(length(canonical_name)) from places').fetchone(); con.close()
   claims,_=collect_official_web_claims(db,MAN); self.assertGreaterEqual(persist_official_web_claims(db,claims),0)
   con=sqlite3.connect(db); after=con.execute('select count(*),sum(length(canonical_name)) from places').fetchone(); con.close(); self.assertEqual(before,after)
 def test_1125_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; shutil.copy2(DB,db); con=sqlite3.connect(db); con.execute("delete from place_evidence where metadata_json like ?",('%'+POLICY+'%',)); con.commit(); con.close()
   claims,_=collect_official_web_claims(db,MAN); a=persist_official_web_claims(db,claims); b=persist_official_web_claims(db,claims); self.assertEqual(a,7); self.assertEqual(b,0)
 def test_1126_public_export_uses_supported_official_fields(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3'; out=Path(td)/'out.json'; shutil.copy2(DB,db); claims,_=collect_official_web_claims(db,MAN); persist_official_web_claims(db,claims); payload=export_prachinlife_json(db,out); byid={p['id']:p for p in payload['places']}
   m=byid['df7d47d4-6772-50f6-a8a9-237b4a28ea62']; self.assertEqual(m['phone'],'0-3721-1586'); self.assertIn('09:00-16:00',m['opening_hours']); self.assertEqual(m['subdistrict'],'หน้าเมือง'); self.assertTrue(m['website'].startswith('https://www.finearts.go.th/'))
   s=byid['57595b16-d24d-5f41-9cf7-8ec261642886']; self.assertIn('เมืองโบราณ',s['description'])
 def test_1127_no_real_image_without_direct_image_evidence(self):
  claims,_=collect_official_web_claims(DB,MAN); self.assertFalse(any(c.field_name=='real_image' for c in claims))

if __name__=='__main__': unittest.main()
