import hashlib, json, shutil, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.coverage_cycle_orchestrator import run_coverage_cycle

ROOT=Path(__file__).resolve().parents[1]
class CoverageCycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=Path(tempfile.mkdtemp()); self.db=self.tmp/'db.sqlite3'; shutil.copy2(ROOT/'data/v2/place_platform_v2.sqlite3',self.db)
 def tearDown(self): shutil.rmtree(self.tmp)
 def sha(self): return hashlib.sha256(self.db.read_bytes()).hexdigest()
 def cycle(self,**kw): return run_coverage_cycle(root_dir=ROOT,database_path=self.db,reports_dir='data/v2/discovery_reports',**kw)
 def test_current_cycle_passes_and_routes_work(self):
  r=self.cycle(); self.assertEqual('PASS',r['status']); self.assertGreaterEqual(r['summary']['work_item_count'],2); self.assertTrue(r['cycle']['discovery_continues'])
 def test_default_is_read_only(self):
  before=self.sha();r=self.cycle();self.assertEqual(before,self.sha());self.assertTrue(r['safety']['database_unchanged']);self.assertFalse(r['safety']['database_writes'])
 def test_pending_candidates_are_not_adopted(self):
  r=self.cycle(); self.assertEqual(0,r['summary']['ready_for_adoption']); self.assertFalse(r['cycle']['controlled_adoption_executed'])
  self.assertTrue(any(x['queue'] in ('manual_confirmation','coordinate_or_manual_confirmation') for x in r['work_items']))
 def test_explicit_commit_with_no_ready_candidate_is_still_noop(self):
  before=self.sha();r=self.cycle(commit_adoption=True);self.assertEqual(before,self.sha());self.assertFalse(r['cycle']['controlled_adoption_executed'])
 def test_safety_contract(self):
  r=self.cycle();s=r['safety'];self.assertTrue(s['explicit_commit_required']);self.assertFalse(s['production_json_writes']);self.assertFalse(s['automatic_publication']);self.assertFalse(s['automatic_evidence_fabrication']);self.assertFalse(s['automatic_conflict_resolution']);self.assertFalse(s['trust_policy_lowered'])

if __name__=='__main__': unittest.main()
