import importlib
import json
import os
import sys
import threading
import types
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def _install_api_dependency_stubs() -> None:
    decision_module = types.ModuleType("place_platform_v2.decision_action_contract_v1")
    decision_module.attach_decision_actions_v1 = lambda payload: {**payload, "actions_attached": True}
    sys.modules[decision_module.__name__] = decision_module

    brain_module = types.ModuleType("place_platform_v2.web_ai_runtime_v1")
    brain_module.run_decision = lambda payload: {"echo": payload, "decision": "stubbed"}
    brain_module.health_payload = lambda: {
        "ok": True,
        "service": "master-super-brain",
        "publication_projection": "stub-projection",
        "human_final_decision": True,
        "repository_ready": True,
    }
    sys.modules[brain_module.__name__] = brain_module


class LocalLifeAPIRegionalContextV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_api_dependency_stubs()
        os.environ["LOCALLIFE_REPOSITORY_ROOT"] = str(ROOT)
        sys.modules.pop("place_platform_v2.locallife_api_v1", None)
        cls.api = importlib.import_module("place_platform_v2.locallife_api_v1")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.api.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        os.environ.pop("LOCALLIFE_REPOSITORY_ROOT", None)

    def _get(self, path: str):
        try:
            with urlopen(self.base + path, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def _post_json(self, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_health_contract_remains_compatible(self):
        status, payload = self._get("/v1/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "locallife-api")
        self.assertEqual(payload["api_version"], "v1")
        self.assertEqual(payload["decision_authority"], "master-super-brain")
        self.assertFalse(payload["canonical_write"])
        self.assertTrue(payload["human_final_decision"])

    def test_existing_decision_post_remains_compatible(self):
        status, payload = self._post_json("/v1/decision", {"message": "hello"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["api_version"], "v1")
        self.assertEqual(payload["result"]["decision"], "stubbed")
        self.assertTrue(payload["result"]["actions_attached"])
        self.assertEqual(payload["result"]["echo"], {"message": "hello"})

    def test_prachinburi_context_get(self):
        status, payload = self._get("/v1/regions/prachinburi/context")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["api_version"], "v1")
        result = payload["result"]
        self.assertEqual(result["contract_version"], "locallife.regional-web-context/v1")
        self.assertEqual(result["product_id"], "th-prachinburi")
        self.assertEqual(result["region_slug"], "prachinburi")
        self.assertEqual(result["brand"], "PrachinLife")
        self.assertFalse(result["freshness"]["place_data_embedded"])
        self.assertNotIn("places", result)

    def test_unknown_region_is_404_fail_closed(self):
        status, payload = self._get("/v1/regions/not-registered/context")
        self.assertEqual(status, 404)
        self.assertEqual(payload, {"ok": False, "error": "region_not_found"})

    def test_malformed_regional_routes_stay_404(self):
        for path in (
            "/v1/regions/prachinburi",
            "/v1/regions/prachinburi/context/extra",
            "/v1/regions//context",
        ):
            with self.subTest(path=path):
                status, payload = self._get(path)
                self.assertEqual(status, 404)
                self.assertEqual(payload, {"ok": False, "error": "not_found"})

    def test_query_string_does_not_change_route_resolution(self):
        status, payload = self._get("/v1/regions/prachinburi/context?ignored=1")
        self.assertEqual(status, 200)
        self.assertEqual(payload["result"]["region_slug"], "prachinburi")

    def test_bad_regional_configuration_returns_sanitized_503(self):
        original = self.api.regional_context_response_payload
        try:
            def broken(_slug):
                raise self.api.RegionalProductContractError("private/path/detail")
            self.api.regional_context_response_payload = broken
            status, payload = self._get("/v1/regions/prachinburi/context")
        finally:
            self.api.regional_context_response_payload = original
        self.assertEqual(status, 503)
        self.assertEqual(payload["error"], "regional_context_not_ready")
        self.assertNotIn("private", json.dumps(payload))

    def test_post_to_context_does_not_create_write_surface(self):
        status, payload = self._post_json("/v1/regions/prachinburi/context", {"x": 1})
        self.assertEqual(status, 404)
        self.assertEqual(payload, {"ok": False, "error": "not_found"})


if __name__ == "__main__":
    unittest.main()
