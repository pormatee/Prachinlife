import unittest
from place_platform_v2.web_ai_runtime_v1 import run_decision

EXPECTED = {
    "801410d8-00e5-58e9-b77e-f681bbdf6f5c",
    "642f3b83-c3f2-5de7-ba26-092261df3cf2",
}

class WebAIPrachinVegetarianRegressionV1(unittest.TestCase):
    def test_exact_real_query_reaches_published_vegetarian_candidates_and_decides(self):
        r = run_decision({
            "text": "หาร้านเจในปราจีนบุรี",
            "context": {},
            "request_id": "webai-prachin-veg-regression-v1",
            "recommendation_limit": 3,
        })
        published = set(r.get("published_candidate_ids") or [])
        compatible = set(r.get("compatible_candidate_ids") or [])
        self.assertTrue(EXPECTED.issubset(published), published)
        self.assertTrue(EXPECTED.issubset(compatible), compatible)
        best = (
            (r.get("explanation") or {}).get("best_fit_candidate_id")
            or (r.get("decision") or {}).get("best_fit_candidate_id")
        )
        self.assertIn(best, EXPECTED)
        self.assertFalse(r.get("needs_user_input"))
        self.assertNotEqual(r.get("status"), "insufficient_data")

if __name__ == "__main__":
    unittest.main()
