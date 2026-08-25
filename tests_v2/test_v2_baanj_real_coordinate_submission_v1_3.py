
import inspect, unittest
from pathlib import Path
import place_platform_v2.controlled_new_place_adoption_core_v2 as core

class V13(unittest.TestCase):
    def test_core_has_candidate_scope(self):
        self.assertIn("candidate_ids", inspect.signature(core.run_controlled_new_place_adoption_core_v2).parameters)
    def test_pilot_uses_exact_real_coordinate(self):
        s=Path("place_platform_v2/baanj_real_coordinate_submission_v1_3.py").read_text(encoding="utf-8")
        self.assertIn("14.076182",s); self.assertIn("100.633498",s)
    def test_pilot_requires_exactly_one_added_place(self):
        s=Path("place_platform_v2/baanj_real_coordinate_submission_v1_3.py").read_text(encoding="utf-8")
        self.assertIn("added!={pid}",s)
        self.assertIn("before_count+1",s)
    def test_no_automatic_review_apply(self):
        s=Path("place_platform_v2/baanj_real_coordinate_submission_v1_3.py").read_text(encoding="utf-8")
        self.assertNotIn("review_coordinate_evidence(",s)
        self.assertNotIn("apply_approved_coordinate_evidence(",s)
if __name__=="__main__": unittest.main()
