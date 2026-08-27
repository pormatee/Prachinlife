import shutil,tempfile,unittest,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from place_platform_v2.coverage_cycle_orchestrator import run_coverage_cycle
from place_platform_v2.operational_work_queue import sync_operational_work_queue
from place_platform_v2.phase5_operational_gate import evaluate_phase5_operational_gate
ROOT=Path(__file__).resolve().parents[1]
class Phase5FinalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=Path(tempfile.mkdtemp());self.db=self.tmp/'db.sqlite3'
  shutil.copy2(ROOT/'data/v2/place_platform_v2.sqlite3',self.db)
  # Isolate tests from an operational queue committed by earlier CLI cycles.
  con=sqlite3.connect(self.db)
  con.execute("drop table if exists operational_work_queue")
  con.commit();con.close()
 def tearDown(self):shutil.rmtree(self.tmp)
 def cycle(self):return run_coverage_cycle(root_dir=ROOT,database_path=self.db,reports_dir='data/v2/discovery_reports')
 def sync(self,items,commit=True):return sync_operational_work_queue(database_path=self.db,work_items=items,province='ปราจีนบุรี',category='vegetarian',commit=commit,now=datetime(2026,8,23,tzinfo=timezone.utc))
 def test_persistent_queue_deduplicates(self):
  c=self.cycle();a=self.sync(c['work_items']);b=self.sync(c['work_items']);self.assertEqual(4,a['inserted']);self.assertEqual(0,b['inserted']);self.assertEqual(4,b['unchanged']);self.assertEqual(4,b['open_queue_count'])
 def test_queue_state_transition_updates_without_duplicate(self):
  c=self.cycle();self.sync(c['work_items']);items=[dict(x) for x in c['work_items']];items[0]['queue']='manual_confirmation';items[0]['next_action']='operator_review';r=self.sync(items);self.assertEqual(1,r['updated']);
  con=sqlite3.connect(self.db);self.assertEqual(4,con.execute("select count(*) from operational_work_queue").fetchone()[0]);con.close()
 def test_missing_work_is_resolved(self):
  c=self.cycle();self.sync(c['work_items']);r=self.sync(c['work_items'][:1]);self.assertEqual(3,r['resolved']);self.assertEqual(1,r['open_queue_count'])
 def test_dry_run_does_not_create_queue_table(self):
  c=self.cycle();r=self.sync(c['work_items'],commit=False);con=sqlite3.connect(self.db);exists=con.execute("select 1 from sqlite_master where type='table' and name='operational_work_queue'").fetchone();con.close();self.assertIsNone(exists);self.assertEqual(4,r['open_queue_count'])
 def test_excluded_non_primary_not_operator_work(self):
  c=self.cycle();items=c['work_items']+[{'candidate_id':None,'name':'mixed','queue':'excluded_non_primary','next_action':'keep','blockers':[]}];r=self.sync(items,commit=False);self.assertEqual(len(c['work_items']),r['active_work_count'])
 def test_scope_is_repeatable(self):
  c=run_coverage_cycle(root_dir=ROOT,database_path=self.db,reports_dir='data/v2/discovery_reports',province='ปราจีนบุรี',category='vegetarian');self.assertEqual('ปราจีนบุรี',c['scope']['province']);self.assertEqual('vegetarian',c['scope']['category'])
 def test_final_gate_passes(self):
  c=self.cycle();q=self.sync(c['work_items']);g=evaluate_phase5_operational_gate(database_path=self.db,cycle=c,queue=q);self.assertEqual('PASS',g['status']);self.assertEqual('ok',g['database']['integrity_check']);self.assertEqual(0,g['database']['foreign_key_errors'])
 def test_safety_contract(self):
  c=self.cycle();q=self.sync(c['work_items']);self.assertFalse(c['safety']['production_json_writes']);self.assertFalse(q['safety']['production_json_writes']);self.assertFalse(q['safety']['automatic_adoption']);self.assertFalse(q['safety']['trust_policy_lowered'])
if __name__=='__main__':unittest.main()
