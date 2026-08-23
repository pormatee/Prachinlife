import json,tempfile,unittest
from pathlib import Path
from place_platform_v2.identity_evidence_followup import followup_identity_evidence
class T(unittest.TestCase):
 def runx(self,obs):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);r=Path(td.name)
  b={'results':[{'name':'ฉันทนา','province':'ปราจีนบุรี','batch_state':'KNOWN_CANDIDATE'}]}
  bp=r/'b.json';op=r/'o.json';bp.write_text(json.dumps(b),encoding='utf-8');op.write_text(json.dumps(obs),encoding='utf-8')
  return followup_identity_evidence(batch_report_path=bp,observations_path=op)
 def test_syndicated_hosts_count_as_one_origin(self):
  x=self.runx([{'name':'ฉันทนา','province':'ปราจีนบุรี','source_family':'a','editorial_origin':'story1'},{'name':'ฉันทนา','province':'ปราจีนบุรี','source_family':'b','editorial_origin':'story1'}])
  self.assertEqual(x['raw_source_family_count'],2);self.assertEqual(x['independent_editorial_origin_count'],1);self.assertEqual(x['identity_outcome'],'SUPPORTED_IDENTITY')
 def test_two_origins_verify(self):
  x=self.runx([{'name':'ฉันทนา','province':'ปราจีนบุรี','source_family':'a','editorial_origin':'story1'},{'name':'ฉันทนา','province':'ปราจีนบุรี','source_family':'b','editorial_origin':'story2'}])
  self.assertEqual(x['identity_outcome'],'VERIFIED_IDENTITY')
 def test_wrong_candidate_excluded(self):
  x=self.runx([{'name':'other','province':'ปราจีนบุรี','source_family':'a','editorial_origin':'story1'}]);self.assertEqual(x['raw_observation_count'],0)
 def test_wrong_province_excluded(self):
  x=self.runx([{'name':'ฉันทนา','province':'จันทบุรี','source_family':'a','editorial_origin':'story1'}]);self.assertEqual(x['raw_observation_count'],0)
 def test_no_writes(self):
  x=self.runx([]);self.assertFalse(x['safety']['canonical_writes']);self.assertFalse(x['safety']['production_json_writes']);self.assertFalse(x['safety']['trust_policy_lowered'])
if __name__=='__main__':unittest.main()
