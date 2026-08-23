import unittest
from pathlib import Path
from place_platform_v2.phase8_production_scale import audit_production_scale
from place_platform_v2.phase8_final_gate import evaluate_phase8_final_gate
ROOT=Path(__file__).resolve().parents[1]
class Phase8FinalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.r=audit_production_scale(root_dir=ROOT,database_path=ROOT/'data/v2/place_platform_v2.sqlite3')
 def test_database_integrity(self):self.assertTrue(self.r['checks']['database_integrity'])
 def test_three_site_configs_same_codebase(self):self.assertTrue(all(self.r['scale']['site_configs'].values()));self.assertTrue(self.r['scale']['same_frontend_codebase'])
 def test_province_scoped_data_model(self):self.assertEqual({'ปราจีนบุรี','ชลบุรี','เชียงใหม่'},set(self.r['scale']['province_place_counts']))
 def test_decision_assistant_preserved(self):self.assertTrue(self.r['checks']['decision_assistant_preserved'])
 def test_v1_fallback_preserved(self):self.assertTrue(self.r['checks']['v1_fallback_preserved'])
 def test_privacy_safe_session_analytics(self):self.assertTrue(self.r['checks']['privacy_safe_usage_analytics'])
 def test_analytics_loaded_before_app(self):self.assertTrue(self.r['checks']['analytics_loaded_before_app'])
 def test_no_automatic_production_or_adoption(self):self.assertFalse(self.r['safety']['production_json_writes']);self.assertFalse(self.r['safety']['automatic_adoption'])
 def test_final_gate_passes(self):self.assertEqual('PASS',evaluate_phase8_final_gate(self.r)['status'])
if __name__=='__main__':unittest.main()
