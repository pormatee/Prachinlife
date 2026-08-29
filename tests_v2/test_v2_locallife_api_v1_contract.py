from __future__ import annotations
import inspect, unittest
from pathlib import Path
from unittest.mock import patch
import place_platform_v2.locallife_api_v1 as api
ROOT=Path(__file__).resolve().parents[1]
class LocalLifeAPIV1ContractTests(unittest.TestCase):
    def test_generic_identity(self):
        h=api.health_payload(); self.assertEqual(h["service"],"locallife-api"); self.assertEqual(h["api_version"],"v1"); self.assertEqual(h["decision_authority"],"master-super-brain"); self.assertFalse(h["canonical_write"]); self.assertTrue(h["human_final_decision"])
    def test_decision_delegates(self):
        payload={"request_id":"contract","text":"หาร้านอาหารในปราจีนบุรี","context":{}}; sentinel={"status":"sentinel"}
        with patch.object(api,"_run_master_brain_decision",return_value=sentinel) as fn:
            self.assertIs(api.decision_payload(payload),sentinel); fn.assert_called_once_with(payload)
    def test_non_object_fails_closed(self):
        with self.assertRaises(ValueError): api.decision_payload([])
    def test_origin_env(self):
        with patch.dict("os.environ",{"LOCALLIFE_ALLOWED_ORIGINS":"https://example.com,https://pormatee.github.io"}):
            self.assertTrue(api._origin_ok("https://example.com")); self.assertFalse(api._origin_ok("https://evil.example"))
    def test_no_duplicate_brain_or_write_authority(self):
        src=inspect.getsource(api)
        for token in ("scorePlace","canonical_place","controlled_publication","adopt_candidate"):
            self.assertNotIn(token,src)
    def test_routes(self):
        src=inspect.getsource(api.Handler); self.assertIn('"/v1/decision"',src); self.assertIn('"/v1/health"',src); self.assertIn('"/healthz"',src)
    def test_provider_independent_container(self):
        s=(ROOT/"Dockerfile.locallife-api").read_text(); self.assertIn("place_platform_v2.locallife_api_v1",s); self.assertNotIn("render.com",s.lower()); self.assertNotIn("railway",s.lower())
    def test_projection_authority(self):
        h=api.health_payload(); self.assertEqual(h["publication_projection"],"authoritative-persisted-read-model"); self.assertTrue(h["repository_ready"])
if __name__ == "__main__": unittest.main()
