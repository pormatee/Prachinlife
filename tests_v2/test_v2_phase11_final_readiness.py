from __future__ import annotations
import json, sqlite3, unittest
from pathlib import Path
from place_platform_v2.phase11_final_readiness import coverage,evidence_profile,final_readiness,MIN_COVERAGE

DB=Path('data/v2/place_platform_v2.sqlite3')
EXP=Path('data/v2/exports/prachinlife_places_v2.json')

class Phase11FinalReadinessTest(unittest.TestCase):
 def test_1141_published_count_frozen_at_220(self):
  cov,p=coverage(EXP); self.assertEqual(p['count'],220); self.assertEqual(len(p['places']),220)
 def test_1142_coverage_never_regresses_below_loop2(self):
  cov,_=coverage(EXP)
  for f,v in MIN_COVERAGE.items(): self.assertGreaterEqual(cov[f],v,(f,cov[f],v))
 def test_1143_exported_evidence_details_have_supported_provenance(self):
  result=final_readiness(DB,EXP); self.assertEqual(result['places'],220)
 def test_1144_candidate_rejected_stale_not_exposed_as_detail_provenance(self):
  _,p=coverage(EXP)
  for x in p['places']:
   for f,m in (x.get('detail_provenance') or {}).items():
    self.assertIn(str(m.get('status') or '').casefold(),{'supported','verified'},(x['id'],f,m))
 def test_1145_supported_detail_evidence_has_traceable_source(self):
  _,p=coverage(EXP); prof=evidence_profile(DB,[x['id'] for x in p['places']])
  self.assertTrue(all(v['missing_provenance']==0 for v in prof.values()),prof)
 def test_1146_real_image_is_fail_closed(self):
  cov,p=coverage(EXP)
  if cov['real_image']==0:
   self.assertTrue(all(not x.get('image_url') for x in p['places']))
  else:
   for x in p['places']:
    if x.get('real_image'):
     self.assertEqual(x.get('image_url'),x.get('real_image'))
     self.assertIn('real_image',x.get('detail_provenance') or {})
 def test_1147_master_image_fallback_contract_remains_installed(self):
  detail=Path('js/core/place-detail.js').read_text(encoding='utf-8')
  image=Path('js/core/place-image.js').read_text(encoding='utf-8')
  self.assertIn('placeImage.renderPlaceImage',detail)
  self.assertIn('data-place-image-type',image)
  self.assertIn('master',image)
 def test_1148_phase11_does_not_require_complete_220_field_coverage(self):
  cov,_=coverage(EXP)
  self.assertLess(cov['description'],220)
  self.assertEqual(MIN_COVERAGE['real_image'],0)

if __name__=='__main__': unittest.main()
