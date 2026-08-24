from __future__ import annotations
import json,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.phase16_verified_update import (
    ALLOWED_FIELDS,validate_verified_update,persist_verified_evidence,run_phase16
)
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"data/v2/place_platform_v2.sqlite3"
PID="801410d8-00e5-58e9-b77e-f681bbdf6f5c"
def sample(**kw):
    x={"place_id":PID,"field_name":"phone","value":"0821389588",
       "source_name":"Independent Official Source",
       "source_url":"https://example.com/verified/sansi",
       "observed_at":"2026-08-24T10:00:00+00:00",
       "trust_tier":"operator_verified_independent_source",
       "community_report":False,
       "community_source_url":"https://example.net/community/report",
       "operator_note":"independently checked"}
    x.update(kw); return x
class Phase16VerifiedUpdateTest(unittest.TestCase):
    def test_1601_scope(self): self.assertEqual(ALLOWED_FIELDS,{"phone","website"})
    def test_1602_community_block(self):
        with self.assertRaises(ValueError): validate_verified_update(sample(community_report=True))
    def test_1603_untrusted_block(self):
        with self.assertRaises(ValueError): validate_verified_update(sample(trust_tier="untrusted_community_report"))
    def test_1604_independent_source(self):
        u="https://example.com/same"
        with self.assertRaises(ValueError): validate_verified_update(sample(source_url=u,community_source_url=u))
    def test_1605_field_block(self):
        with self.assertRaises(ValueError): validate_verified_update(sample(field_name="description"))
    def test_1606_dry_zero_write(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"d.sqlite3"; shutil.copy2(DB,db); before=db.read_bytes()
            r=persist_verified_evidence(db,(validate_verified_update(sample()),),commit=False)
            self.assertEqual(before,db.read_bytes()); self.assertTrue(r["database_unchanged"])
    def test_1607_supported_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"d.sqlite3"; shutil.copy2(DB,db)
            r=persist_verified_evidence(db,(validate_verified_update(sample()),),commit=True)
            self.assertEqual(r["inserted_count"],1)
            con=sqlite3.connect(db)
            row=con.execute("select status,metadata_json from place_evidence where place_id=? and field_name='phone' order by rowid desc limit 1",(PID,)).fetchone()
            con.close(); self.assertEqual(row[0],"supported")
            md=json.loads(row[1]); self.assertEqual(md["persistence"],"phase3_5_controlled_web_evidence")
    def test_1608_missing_input_safe_noop(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_phase16(repo_root=ROOT,database_path=DB,verified_updates_path=Path(td)/"missing.json",commit=False)
            self.assertEqual(r["status"],"NO_ELIGIBLE_VERIFIED_UPDATE")
            self.assertFalse(r["canonical_mutation"]); self.assertFalse(r["production_mutation"])
    def test_1609_dry_real_db_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"u.json"; p.write_text(json.dumps([sample()]),encoding="utf-8"); before=DB.read_bytes()
            r=run_phase16(repo_root=ROOT,database_path=DB,verified_updates_path=p,commit=False)
            self.assertEqual(before,DB.read_bytes()); self.assertIn(r["status"],{"READY","BLOCKED"})
    def test_1610_publication_rollback_contract(self):
        t=(ROOT/"place_platform_v2/controlled_production_publication.py").read_text(encoding="utf-8")
        self.assertIn("automatic rollback hash verification failed",t); self.assertIn("rollback_available",t)
    def test_1611_adoption_revision_contract(self):
        t=(ROOT/"place_platform_v2/controlled_canonical_adoption.py").read_text(encoding="utf-8")
        self.assertIn('ALLOWED_FIELDS = frozenset({"phone", "website"})',t); self.assertIn("place_revisions",t)
    def test_1612_phase15_hold_preserved(self):
        t=(ROOT/"place_platform_v2/admin_drafts.py").read_text(encoding="utf-8")
        self.assertIn("community report is HOLD-only",t)
if __name__=="__main__": unittest.main()
