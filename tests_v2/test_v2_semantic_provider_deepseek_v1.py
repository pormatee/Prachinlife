import json
import os
import unittest
from unittest import mock

from place_platform_v2.generic_semantic_language_brain_v1 import (
    DEFAULT_DEEPSEEK_ENDPOINT,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_OPENAI_MODEL,
    DeepSeekResponsesSemanticProviderV1,
    OpenAIResponsesSemanticProviderV1,
    SemanticLanguageProviderError,
    _provider_from_environment,
    build_semantic_input_v1,
    interpret_semantic_language_v1,
    semantic_provider_health_v1,
)


class T(unittest.TestCase):
    def test_01_deepseek_defaults_match_responses_api(self):
        provider = DeepSeekResponsesSemanticProviderV1(api_key="test-key")
        self.assertEqual("deepseek", provider.name)
        self.assertEqual("deepseek-v4-flash", DEFAULT_DEEPSEEK_MODEL)
        self.assertEqual("https://api.deepseek.com/responses", DEFAULT_DEEPSEEK_ENDPOINT)
        self.assertEqual(DEFAULT_DEEPSEEK_MODEL, provider.model)

    def test_02_deepseek_uses_json_schema_structured_output(self):
        provider = DeepSeekResponsesSemanticProviderV1(api_key="test-key")
        body = provider._request_payload(build_semantic_input_v1("ช่วยหาร้านที่เหมาะกับแม่", {}))
        self.assertEqual(DEFAULT_DEEPSEEK_MODEL, body["model"])
        self.assertEqual("json_schema", body["text"]["format"]["type"])
        self.assertEqual("prachinlife_semantic_language_v1", body["text"]["format"]["name"])
        self.assertIn("schema", body["text"]["format"])
        self.assertEqual("none", body["reasoning"]["effort"])
        self.assertFalse(body["stream"])
        self.assertNotIn("store", body)

    def test_03_deepseek_response_parser_ignores_reasoning_and_reads_message(self):
        semantic_json = json.dumps({
            "conversation_act": "new_request",
            "goal": "find food",
            "category": "eat",
            "decision_object": "restaurant",
            "location_text": None,
            "province": None,
            "near_me": None,
            "temporal_context": None,
            "criteria": [],
            "reference": {"kind": "none", "ordinal": None, "name": None},
            "fact_key": None,
            "comparison_criterion": None,
            "explanation_focus": None,
            "clarification": {"needed": False, "field": None, "question": None},
            "confidence": 0.9,
        }, ensure_ascii=False)
        data = {
            "output": [
                {
                    "type": "reasoning",
                    "content": [{"type": "reasoning_text", "text": "internal"}],
                },
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": semantic_json}],
                },
            ]
        }
        self.assertEqual(
            semantic_json,
            DeepSeekResponsesSemanticProviderV1._extract_output_text(data),
        )

    def test_04_explicit_deepseek_environment_selects_deepseek(self):
        env = {
            "PRACHINLIFE_SEMANTIC_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "deepseek-test",
            "OPENAI_API_KEY": "",
            "PRACHINLIFE_SEMANTIC_MODEL": "",
            "PRACHINLIFE_SEMANTIC_ENDPOINT": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            provider = _provider_from_environment()
        self.assertIsInstance(provider, DeepSeekResponsesSemanticProviderV1)
        self.assertEqual(DEFAULT_DEEPSEEK_MODEL, provider.model)

    def test_05_auto_selects_deepseek_when_only_deepseek_key_exists(self):
        env = {
            "PRACHINLIFE_SEMANTIC_PROVIDER": "auto",
            "DEEPSEEK_API_KEY": "deepseek-test",
            "OPENAI_API_KEY": "",
            "PRACHINLIFE_SEMANTIC_MODEL": "",
            "PRACHINLIFE_SEMANTIC_ENDPOINT": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            provider = _provider_from_environment()
        self.assertIsInstance(provider, DeepSeekResponsesSemanticProviderV1)

    def test_06_auto_preserves_openai_priority_when_both_keys_exist(self):
        env = {
            "PRACHINLIFE_SEMANTIC_PROVIDER": "auto",
            "DEEPSEEK_API_KEY": "deepseek-test",
            "OPENAI_API_KEY": "openai-test",
            "PRACHINLIFE_SEMANTIC_MODEL": "",
            "PRACHINLIFE_SEMANTIC_ENDPOINT": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            provider = _provider_from_environment()
        self.assertIsInstance(provider, OpenAIResponsesSemanticProviderV1)
        self.assertEqual(DEFAULT_OPENAI_MODEL, provider.model)

    def test_07_explicit_deepseek_missing_key_fails_safe_without_network(self):
        env = {
            "PRACHINLIFE_SEMANTIC_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "",
            "OPENAI_API_KEY": "",
            "PRACHINLIFE_SEMANTIC_MODEL": "",
            "PRACHINLIFE_SEMANTIC_ENDPOINT": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result = interpret_semantic_language_v1("หาร้านเจ", {})
        self.assertEqual("fallback_error", result.status)
        self.assertEqual("configuration", result.provider)
        self.assertEqual("deepseek_api_key_missing", result.error_code)

    def test_08_deepseek_responses_rejects_unsupported_model_fail_closed(self):
        with self.assertRaises(SemanticLanguageProviderError):
            DeepSeekResponsesSemanticProviderV1(
                api_key="test-key",
                model="deepseek-v4-pro",
            )

    def test_09_health_reports_deepseek_without_exposing_key(self):
        env = {
            "PRACHINLIFE_SEMANTIC_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "super-secret-key",
            "OPENAI_API_KEY": "",
            "PRACHINLIFE_SEMANTIC_MODEL": "deepseek-v4-flash",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            health = semantic_provider_health_v1()
        self.assertTrue(health["enabled"])
        self.assertEqual("deepseek", health["provider"])
        self.assertEqual("deepseek-v4-flash", health["model"])
        self.assertTrue(health["api_key_present"])
        self.assertNotIn("super-secret-key", json.dumps(health))

    def test_10_provider_health_preserves_no_ranking_authority(self):
        env = {
            "PRACHINLIFE_SEMANTIC_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "test-key",
            "OPENAI_API_KEY": "",
            "PRACHINLIFE_SEMANTIC_MODEL": "deepseek-v4-flash",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            health = semantic_provider_health_v1()
        self.assertFalse(health["ranking_authority"])
        self.assertFalse(health["exact_location_sent_to_language_model"])


if __name__ == "__main__":
    unittest.main()
