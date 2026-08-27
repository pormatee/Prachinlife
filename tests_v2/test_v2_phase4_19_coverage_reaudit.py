import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.phase4_coverage_reaudit import audit_phase4_coverage
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/v2/place_platform_v2.sqlite3'; RD=ROOT/'data/v2/discovery_reports'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Phase419(unittest.TestCase):
 def test_current_audit_is_read_only_and_final_gate_ready(self):
  b=sha(DB);r=audit_phase4_coverage(database_path=DB,reports_dir=RD)
  self.assertEqual('PASS',r['status']);self.assertEqual(b,sha(DB));self.assertTrue(r['safety']['read_only_audit']);self.assertTrue(r['closure_assessment']['phase4_final_gate_ready'])
 def test_current_funnel_accounts_for_pending_followup_and_exclusions(self):
  r=audit_phase4_coverage(database_path=DB,reports_dir=RD)
  self.assertEqual(4,r['funnel']['state_counts']['PRECANONICAL']);self.assertEqual(2,r['funnel']['state_counts']['PENDING_CONFIRMATION']);self.assertEqual(3,r['funnel']['state_counts']['EXCLUDED_GENERAL_OR_MIXED_SCOPE']);self.assertEqual(0,r['funnel']['state_counts']['READY_FOR_CONTROLLED_ADOPTION'])
  self.assertIn('ฉันทนา',r['funnel']['followup_names']);self.assertIn('มังสวิรัติ🥕🥦🍞🫘',r['funnel']['followup_names'])
 def test_prachin_primary_vegetarian_canonical_is_measured(self):
  r=audit_phase4_coverage(database_path=DB,reports_dir=RD)
  self.assertGreaterEqual(r['canonical']['province_place_count'],1);self.assertGreaterEqual(r['canonical']['primary_category_count'],1);self.assertIn('อาหารเจ ซั่นสี่',r['canonical']['primary_names'])
 def test_no_real_world_completeness_claim(self):
  r=audit_phase4_coverage(database_path=DB,reports_dir=RD)
  self.assertFalse(r['closure_assessment']['real_world_completeness_claimed']);self.assertTrue(r['closure_assessment']['coverage_work_remains']);self.assertTrue(r['closure_assessment']['pending_does_not_block_discovery'])
 def test_safety_contract(self):
  r=audit_phase4_coverage(database_path=DB,reports_dir=RD)
  for k in ['database_writes','canonical_writes','precanonical_writes','pending_writes','production_json_writes','trust_policy_lowered']:self.assertFalse(r['safety'][k])
if __name__=='__main__':unittest.main()
