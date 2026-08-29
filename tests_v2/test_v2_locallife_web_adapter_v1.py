import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT = ROOT / "js/core/locallife-api-client-v1.js"
INDEX = ROOT / "index.html"

class LocalLifeWebAdapterV1ContractTest(unittest.TestCase):
    def test_client_exists_and_uses_public_api(self):
        text = CLIENT.read_text(encoding="utf-8")
        self.assertIn("https://locallife-api.onrender.com", text)
        self.assertIn('"/v1/health"', text)
        self.assertIn('"/v1/decision"', text)

    def test_client_is_transport_only(self):
        text = CLIENT.read_text(encoding="utf-8").lower()
        forbidden = [
            "organic_score",
            "regret_risk",
            "constraint_fit",
            "preference_fit",
            "candidate.sort",
            ".sort(",
            "recommend(",
            "scoreplace",
        ]
        for token in forbidden:
            self.assertNotIn(token, text, token)

    def test_no_canonical_or_publication_write_authority(self):
        text = CLIENT.read_text(encoding="utf-8").lower()
        for token in [
            "canonical_write",
            "commit_controlled_production_publication",
            "rollback_controlled_production_publication",
            "automatic_publication",
        ]:
            self.assertNotIn(token, text, token)

    def test_index_loads_adapter_before_app(self):
        html = INDEX.read_text(encoding="utf-8")
        adapter = html.find("js/core/locallife-api-client-v1.js")
        app = re.search(r'<script\b[^>]*\bsrc=["\']app\.js', html, re.I)
        self.assertGreaterEqual(adapter, 0)
        self.assertIsNotNone(app)
        self.assertLess(adapter, app.start())

    def test_single_adapter_load(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertEqual(html.count("js/core/locallife-api-client-v1.js"), 1)

    def test_api_exposed_under_existing_namespace(self):
        text = CLIENT.read_text(encoding="utf-8")
        self.assertIn("global.PrachinLife.core.localLifeApiV1", text)
        self.assertIn("Object.freeze", text)

if __name__ == "__main__":
    unittest.main()
