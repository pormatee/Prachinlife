import json,sqlite3,tempfile,shutil,unittest
from pathlib import Path
from place_platform_v2.phase6_data_expansion import audit_prachinburi_data_quality,build_expansion_work,CORE_CATEGORIES
from place_platform_v2.operational_work_queue import sync_operational_work_queue
from place_platform_v2.phase6_final_gate import evaluate_phase6_final_gate
ROOT=Path(__file__).resolve().parents[1]
class Phase6FinalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=Path(tempfile.mkdtemp());self.db=self.tmp/'db.sqlite3';shutil.copy2(ROOT/'data/v2/place_platform_v2.sqlite3',self.db)
  con=sqlite3.connect(self.db);con.execute('drop table if exists operational_work_queue');con.commit();con.close()
 def tearDown(self):shutil.rmtree(self.tmp)
 def audit(self):return audit_prachinburi_data_quality(database_path=self.db)
 def test_all_core_categories_accounted(self):self.assertEqual(set(CORE_CATEGORIES),set(self.audit()['categories']))
 def test_current_prachinburi_inventory_is_visible(self):self.assertGreaterEqual(self.audit()['canonical_place_count'],200)
 def test_quality_gaps_are_explicit(self):
  a=self.audit();self.assertEqual(a['categories']['fuel']['canonical_count'],111);self.assertEqual(a['categories']['fuel']['quality_gaps']['address'],111)
 def test_thin_categories_route_to_discovery(self):
  w=build_expansion_work(audit=self.audit());d={x['category_scope']:x for x in w};self.assertEqual('coverage_discovery',d['vegetarian']['queue']);self.assertEqual('coverage_discovery',d['pharmacy']['queue'])
 def test_established_categories_route_to_quality(self):
  w=build_expansion_work(audit=self.audit());d={x['category_scope']:x for x in w};self.assertEqual('quality_enrichment',d['fuel']['queue']);self.assertEqual('quality_enrichment',d['restaurant']['queue'])
 def test_queue_deduplicates_multi_category_work(self):
  w=build_expansion_work(audit=self.audit());a=sync_operational_work_queue(database_path=self.db,work_items=w,province='ปราจีนบุรี',category='all',commit=True);b=sync_operational_work_queue(database_path=self.db,work_items=w,province='ปราจีนบุรี',category='all',commit=True);self.assertEqual(len(w),a['inserted']);self.assertEqual(0,b['inserted']);self.assertEqual(len(w),b['unchanged'])
 def test_dry_run_does_not_create_queue(self):
  w=build_expansion_work(audit=self.audit());sync_operational_work_queue(database_path=self.db,work_items=w,province='ปราจีนบุรี',category='all',commit=False);con=sqlite3.connect(self.db);e=con.execute("select 1 from sqlite_master where type='table' and name='operational_work_queue'").fetchone();con.close();self.assertIsNone(e)
 def test_gate_passes_without_claiming_completeness(self):
  audit=self.audit();w=build_expansion_work(audit=audit);q=sync_operational_work_queue(database_path=self.db,work_items=w,province='ปราจีนบุรี',category='all',commit=False);r={'quality_audit':audit,'summary':{'category_work_items':len(w),'discovery_continues':True}};g=evaluate_phase6_final_gate(database_path=self.db,report=r,queue=q);self.assertEqual('PASS',g['status']);self.assertFalse(audit['real_world_completeness_claimed'])
if __name__=='__main__':unittest.main()
