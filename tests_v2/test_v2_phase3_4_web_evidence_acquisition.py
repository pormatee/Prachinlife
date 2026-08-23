import json, shutil, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.web_evidence_acquisition import (
    _name_similarity, _normalize_phone, acquire_independent_web_evidence,
)

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/v2/place_platform_v2.sqlite3'
PLAN=ROOT/'data/v2/discovery_reports/targeted_production_enrichment_v2.json'

class TestPhase34WebEvidenceAcquisition(unittest.TestCase):
    def _run(self, observations):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); db=td/'db.sqlite3'; shutil.copy2(DB,db)
            manifest=td/'obs.json'; manifest.write_text(json.dumps({'observations':observations},ensure_ascii=False),encoding='utf-8')
            before=db.read_bytes()
            r=acquire_independent_web_evidence(database_path=db,targeted_plan_path=PLAN,repo_root=ROOT,observation_manifest_path=manifest,observed_at=datetime(2026,8,23,tzinfo=timezone.utc))
            self.assertEqual(before,db.read_bytes())
            return r

    def test_name_similarity_handles_descriptive_suffixes(self):
        self.assertGreaterEqual(_name_similarity('Anchan','Anchan Vegetarian Restaurant'),.9)
        self.assertGreaterEqual(_name_similarity('Baan Unrak','Baan Unrak Vegetarian Restaurant & Bakery'),.9)

    def test_phone_normalization(self):
        self.assertEqual(_normalize_phone('+66 83 581 1689'),'+66835811689')
        self.assertIsNone(_normalize_phone('123'))

    def test_accepts_candidate_only_with_provenance(self):
        plan=json.loads(PLAN.read_text(encoding='utf-8')); x=plan['queue'][0]
        r=self._run([{'target_rank':1,'place_id':x['place_id'],'observed_name':'Anchan Vegetarian Restaurant','province':'เชียงใหม่','source_name':'Official','source_url':'https://anchanvegetarian.com/','source_record_id':'home','phone':'+66 83 581 1689','website':'https://anchanvegetarian.com/'}])
        self.assertEqual(r['candidate_claim_count'],2)
        self.assertTrue(all(x['status']=='candidate' for x in r['claims']))
        self.assertFalse(r['safety']['evidence_writes']); self.assertFalse(r['safety']['production_json_writes'])

    def test_blocks_place_id_mismatch(self):
        r=self._run([{'target_rank':1,'place_id':'bad','observed_name':'Anchan','province':'เชียงใหม่','source_name':'x','source_url':'https://example.com','source_record_id':'1','phone':'0812345678'}])
        self.assertEqual(r['blocked_counts'],{'place_id_mismatch':1}); self.assertEqual(r['candidate_claim_count'],0)

    def test_blocks_province_conflict(self):
        plan=json.loads(PLAN.read_text(encoding='utf-8')); x=plan['queue'][0]
        r=self._run([{'target_rank':1,'place_id':x['place_id'],'observed_name':'Anchan','province':'ภูเก็ต','source_name':'x','source_url':'https://example.com','source_record_id':'1','phone':'0812345678'}])
        self.assertEqual(r['blocked_counts'],{'province_conflict':1})

    def test_blocks_name_conflict(self):
        plan=json.loads(PLAN.read_text(encoding='utf-8')); x=plan['queue'][0]
        r=self._run([{'target_rank':1,'place_id':x['place_id'],'observed_name':'Completely Different Shop','province':'เชียงใหม่','source_name':'x','source_url':'https://example.com','source_record_id':'1','phone':'0812345678'}])
        self.assertEqual(r['blocked_counts'],{'identity_name_conflict':1})

    def test_blocks_osm_as_independent_web(self):
        plan=json.loads(PLAN.read_text(encoding='utf-8')); x=plan['queue'][0]
        r=self._run([{'target_rank':1,'place_id':x['place_id'],'observed_name':'Anchan','province':'เชียงใหม่','source_name':'OSM','source_url':'https://www.openstreetmap.org/node/1','source_record_id':'1','phone':'0812345678'}])
        self.assertEqual(r['blocked_counts'],{'source_is_not_independent_web':1})

    def test_repository_pilot_manifest_is_safe_and_nonempty(self):
        r=acquire_independent_web_evidence(database_path=DB,targeted_plan_path=PLAN,repo_root=ROOT,observation_manifest_path=ROOT/'data/v2/discovery_reports/phase3_4_web_observations.json',observed_at=datetime(2026,8,23,tzinfo=timezone.utc))
        self.assertEqual(r['observation_count'],8)
        self.assertGreaterEqual(r['candidate_place_count'],6)
        self.assertGreaterEqual(r['candidate_claim_count'],8)
        self.assertEqual(r['blocked_counts'],{})
        self.assertTrue(r['safety']['database_unchanged']); self.assertFalse(r['safety']['trust_policy_lowered'])

if __name__=='__main__': unittest.main()
