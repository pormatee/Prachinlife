import json,shutil,tempfile,unittest
from pathlib import Path
from place_platform_v2.phase4_final_gate import run_phase4_final_gate

ROOT=Path(__file__).resolve().parents[1]
class Phase420FinalGateTests(unittest.TestCase):
 def setUp(self):
  self.t=Path(tempfile.mkdtemp());(self.t/'data/v2/discovery_reports').mkdir(parents=True)
  shutil.copy2(ROOT/'data/v2/place_platform_v2.sqlite3',self.t/'data/v2/place_platform_v2.sqlite3')
  for n in (15,16,17,18,19):shutil.copy2(ROOT/f'PHASE4_{n}_CHECKPOINT.txt',self.t/f'PHASE4_{n}_CHECKPOINT.txt')
  for f in ('phase4_19_coverage_reaudit_v2.json','controlled_new_place_adoption_machine_v2.json'):shutil.copy2(ROOT/'data/v2/discovery_reports'/f,self.t/'data/v2/discovery_reports'/f)
 def tearDown(self):shutil.rmtree(self.t)
 def run_gate(self):return run_phase4_final_gate(root_dir=self.t)
 def test_current_state_passes(self):self.assertEqual(self.run_gate()['status'],'PASS')
 def test_gate_is_read_only(self):
  p=self.t/'data/v2/place_platform_v2.sqlite3';before=p.read_bytes();r=self.run_gate();self.assertEqual(before,p.read_bytes());self.assertTrue(r['safety']['database_unchanged'])
 def test_failed_checkpoint_blocks_freeze(self):
  p=self.t/'PHASE4_17_CHECKPOINT.txt';p.write_text(p.read_text().replace('STATUS = PASS','STATUS = BLOCKED',1));r=self.run_gate();self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['freeze']['freeze_ready'])
 def test_ready_candidate_blocks_freeze(self):
  p=self.t/'data/v2/discovery_reports/controlled_new_place_adoption_machine_v2.json';x=json.loads(p.read_text());x['eligible_count']=1;x['ready_count']=1;p.write_text(json.dumps(x));self.assertEqual(self.run_gate()['status'],'BLOCKED')
 def test_open_coverage_is_nonblocking_and_explicit(self):
  r=self.run_gate();self.assertTrue(r['coverage_snapshot']['coverage_work_remains']);self.assertFalse(r['coverage_snapshot']['real_world_completeness_claimed']);self.assertTrue(r['freeze']['open_work_carries_forward'])
if __name__=='__main__':unittest.main()
