import json,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.pending_review_queue import queue_pending_reviews
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def fixture(self):
  td=tempfile.TemporaryDirectory(); r=Path(td.name); db=r/'db.sqlite3'; shutil.copy2(ROOT/'data/v2/place_platform_v2.sqlite3',db); c=sqlite3.connect(db); c.execute('DROP TABLE IF EXISTS precanonical_pending_review'); c.commit(); c.close(); return td,r,db
 def invoke(self,db,commit=False):
  return queue_pending_reviews(database_path=db,adoption_report_path=ROOT/'data/v2/discovery_reports/new_place_adoption_review_v2.json',lifecycle_report_path=ROOT/'data/v2/discovery_reports/lifecycle_conflict_resolution_v2.json',direct_confirmation_report_path=ROOT/'data/v2/discovery_reports/direct_lifecycle_confirmation_v2.json',coverage_report_path=ROOT/'data/v2/discovery_reports/discovery_coverage_audit_v2.json',commit=commit)
 def test_detects_unresolved_candidate(self):
  td,r,db=self.fixture(); self.addCleanup(td.cleanup); x=self.invoke(db); self.assertEqual(x['pending_candidate_count'],1); self.assertEqual(x['pending_candidates'][0]['name'],'ต้นหลิวอาหารเจ')
 def test_commit_queues_once_and_is_idempotent(self):
  td,r,db=self.fixture(); self.addCleanup(td.cleanup); a=self.invoke(db,True); b=self.invoke(db,True); self.assertEqual(a['inserted_queue_count'],1); self.assertEqual(b['inserted_queue_count'],0); self.assertEqual(b['already_queued_count'],1); self.assertEqual(b['pending_queue_total'],1)
 def test_only_queue_table_changes(self):
  td,r,db=self.fixture(); self.addCleanup(td.cleanup); x=self.invoke(db,True); self.assertTrue(x['safety']['non_queue_tables_unchanged']); self.assertFalse(x['safety']['production_json_writes'])
 def test_pending_does_not_block_discovery(self):
  td,r,db=self.fixture(); self.addCleanup(td.cleanup); x=self.invoke(db,True); self.assertTrue(x['discovery_continues']); self.assertFalse(x['safety']['pending_candidate_blocks_discovery']); self.assertIsNotNone(x['next_discovery_work'])
 def test_no_auto_adopt_or_publish(self):
  td,r,db=self.fixture(); self.addCleanup(td.cleanup); x=self.invoke(db,True); self.assertFalse(x['safety']['automatic_adoption']); self.assertFalse(x['safety']['automatic_publication']); self.assertFalse(x['safety']['trust_policy_lowered'])
if __name__=='__main__': unittest.main()
