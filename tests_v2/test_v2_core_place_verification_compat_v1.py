import unittest
from place_platform_v2.core_place_verification_v2 import evaluate_place

class CorePlaceVerificationV2CompatTest(unittest.TestCase):
 def test_verified_exact_is_near_me_ready(self):
  r=evaluate_place(identity_outcome='VERIFIED_IDENTITY',source_families=['a','b'],coordinate_outcome='EXACT_COORDINATES_VERIFIED')
  self.assertEqual(r.state.value,'VERIFIED_NEAR_ME_READY');self.assertTrue(r.canonical_eligible);self.assertTrue(r.near_me_eligible)
 def test_verified_without_coordinates_keeps_place_but_not_near_me(self):
  r=evaluate_place(identity_outcome='VERIFIED_IDENTITY',source_families=['a','b'],coordinate_outcome='EXACT_COORDINATES_UNRESOLVED')
  self.assertEqual(r.state.value,'VERIFIED_PLACE_COORDINATE_PENDING');self.assertTrue(r.canonical_eligible);self.assertFalse(r.near_me_eligible)
 def test_single_source_does_not_oververify(self):
  r=evaluate_place(identity_outcome='VERIFIED_IDENTITY',source_families=['a'])
  self.assertEqual(r.state.value,'CANDIDATE_OR_REVIEW');self.assertFalse(r.canonical_eligible)
 def test_lifecycle_review_stays_review(self):
  r=evaluate_place(identity_outcome='VERIFIED_IDENTITY',source_families=['a','b'],review_flags=['open_vs_closed_source_conflict'])
  self.assertEqual(r.state.value,'CANDIDATE_OR_REVIEW')
 def test_category_not_part_of_contract(self):
  r=evaluate_place(identity_outcome='VERIFIED_IDENTITY',source_families=['official','osm'])
  self.assertTrue(r.canonical_eligible)

if __name__=='__main__':unittest.main()
