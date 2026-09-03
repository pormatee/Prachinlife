import json
import os
import unittest
from pathlib import Path
from unittest import mock

from place_platform_v2.generic_semantic_language_brain_v1 import (
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_OPENAI_MODEL,
    OpenAIResponsesSemanticProviderV1,
    SEMANTIC_OUTPUT_SCHEMA,
    SemanticLanguageProviderError,
    SemanticLanguageProviderV1,
    build_semantic_input_v1,
    interpret_semantic_language_v1,
)
from place_platform_v2.semantic_conversation_understanding_v1 import (
    SemanticConversationStateV1,
    resolve_semantic_turn_v1,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "place_platform_v2/web_ai_runtime_v1.py").read_text(encoding="utf-8")
JS = (ROOT / "js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
GENERIC = (ROOT / "place_platform_v2/generic_semantic_language_brain_v1.py").read_text(encoding="utf-8")
SEMANTIC = (ROOT / "place_platform_v2/semantic_conversation_understanding_v1.py").read_text(encoding="utf-8")


def meaning(**updates):
    base = {
        "conversation_act": "new_request",
        "goal": "find a suitable local option",
        "category": "go",
        "decision_object": "destination",
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
        "confidence": 0.92,
    }
    base.update(updates)
    return base


class FakeProvider(SemanticLanguageProviderV1):
    name = "fake"
    model = "fake-semantic"

    def __init__(self, output):
        self.output = output
        self.seen = None

    def interpret(self, semantic_input):
        self.seen = semantic_input
        return self.output


class FailingProvider(SemanticLanguageProviderV1):
    name = "fake"
    model = "fake-semantic"

    def interpret(self, semantic_input):
        raise SemanticLanguageProviderError("simulated_provider_failure")


class T(unittest.TestCase):
    def state(self, **updates):
        base = dict(
            turn_index=4,
            active_request_text="หาร้านเจรังสิต",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
            candidate_ids=("A", "B", "C"),
        )
        base.update(updates)
        return SemanticConversationStateV1(**base)

    def test_01_input_never_sends_exact_gps_or_candidate_ids(self):
        payload = build_semantic_input_v1(
            "ช่วยดูอันที่เหมาะกับแม่หน่อย",
            {
                "current_location": [14.12345, 100.98765],
                "location_text": "รังสิต",
                "conversation_state": self.state().to_payload(),
            },
            [{"candidate_id": "SECRET-A", "name": "ร้านเอ"}],
        )
        blob = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("14.12345", blob)
        self.assertNotIn("100.98765", blob)
        self.assertNotIn("SECRET-A", blob)
        self.assertTrue(payload["runtime_context"]["has_current_location"])
        self.assertEqual("ร้านเอ", payload["candidate_references"][0]["name"])

    def test_02_provider_contract_contains_no_ranking_or_sponsor_authority(self):
        blob = json.dumps(SEMANTIC_OUTPUT_SCHEMA, ensure_ascii=False).casefold()
        for forbidden in ("ranking", "rank_score", "sponsor", "provider_score"):
            self.assertNotIn(forbidden, blob)
        self.assertIn("conversation_act", blob)
        self.assertIn("criteria", blob)

    def test_03_fake_model_can_interpret_unseen_language_without_phrase_rules(self):
        fake = FakeProvider(meaning(
            conversation_act="new_request",
            category="go",
            decision_object="destination",
            criteria=[{
                "key": "accessibility",
                "value": "comfortable_for_elderly",
                "polarity": "prefer",
                "importance": "soft",
            }],
        ))
        result = interpret_semantic_language_v1(
            "อยากพาคุณย่าออกไปเปลี่ยนบรรยากาศแบบไม่ลำบากแกมาก",
            {},
            provider=fake,
        )
        self.assertTrue(result.used_model)
        resolved = resolve_semantic_turn_v1(
            "อยากพาคุณย่าออกไปเปลี่ยนบรรยากาศแบบไม่ลำบากแกมาก",
            {},
            language_interpretation=result.meaning,
        )
        self.assertEqual("new", resolved.mode)
        self.assertEqual("go", resolved.state.category)
        self.assertEqual("destination", resolved.state.decision_object)
        self.assertIn("prefer:accessibility=comfortable_for_elderly", resolved.state.semantic_criteria)
        self.assertEqual("new_request", resolved.state.language_act)

    def test_04_generic_reference_fact_resolves_ordinal_from_model(self):
        m = meaning(
            conversation_act="reference_fact",
            category=None,
            decision_object=None,
            reference={"kind": "candidate_ordinal", "ordinal": 2, "name": None},
            fact_key="phone",
        )
        resolved = resolve_semantic_turn_v1(
            "งั้นตัวรองจากนั้นติดต่อยังไง",
            {"conversation_state": self.state().to_payload()},
            language_interpretation={"schema_version": "GENERIC-SEMANTIC-MEANING-V1", **m},
        )
        self.assertEqual("reference_fact", resolved.mode)
        self.assertEqual("B", resolved.state.referenced_candidate_id)
        self.assertEqual("phone", resolved.state.reference_fact)

    def test_05_generic_compare_distance_uses_prior_candidates(self):
        m = meaning(
            conversation_act="compare",
            category=None,
            decision_object=None,
            comparison_criterion="distance",
        )
        resolved = resolve_semantic_turn_v1(
            "ถ้าตัดเรื่องอื่นออก เอาแค่ไม่ต้องเดินทางเยอะ",
            {"conversation_state": self.state().to_payload()},
            language_interpretation={"schema_version": "GENERIC-SEMANTIC-MEANING-V1", **m},
        )
        self.assertEqual("comparison", resolved.mode)
        self.assertEqual(("A", "B", "C"), resolved.state.candidate_ids)
        self.assertEqual("distance", resolved.state.comparison_criterion)
        self.assertTrue(resolved.state.near_me)

    def test_06_generic_explanation_act_does_not_need_why_keyword(self):
        m = meaning(
            conversation_act="explain_decision",
            category=None,
            decision_object=None,
            explanation_focus="why",
        )
        resolved = resolve_semantic_turn_v1(
            "ช่วยแจกแจงฐานที่ใช้ลงความเห็นเมื่อกี้",
            {"conversation_state": self.state().to_payload()},
            language_interpretation={"schema_version": "GENERIC-SEMANTIC-MEANING-V1", **m},
        )
        self.assertEqual("decision_explanation", resolved.mode)
        self.assertEqual("why", resolved.state.explanation_request)
        self.assertEqual(("A", "B", "C"), resolved.state.candidate_ids)

    def test_07_low_confidence_model_meaning_falls_back_to_existing_understanding(self):
        m = meaning(confidence=0.1, category="go", decision_object="destination")
        resolved = resolve_semantic_turn_v1(
            "หาร้านเจ",
            {},
            language_interpretation={"schema_version": "GENERIC-SEMANTIC-MEANING-V1", **m},
        )
        self.assertEqual("new", resolved.mode)
        self.assertEqual("vegetarian", resolved.state.category)
        self.assertIsNone(resolved.state.language_act)

    def test_08_provider_failure_is_fail_safe_deterministic_fallback(self):
        result = interpret_semantic_language_v1("หาร้านเจ", {}, provider=FailingProvider())
        self.assertFalse(result.used_model)
        self.assertEqual("fallback_error", result.status)
        self.assertEqual("simulated_provider_failure", result.error_code)
        self.assertIsNone(result.meaning)

    def test_09_candidate_name_binding_is_exact_not_fuzzy(self):
        fake = FakeProvider(meaning(
            conversation_act="reference_fact",
            category=None,
            decision_object=None,
            reference={"kind": "candidate_name", "ordinal": None, "name": "บ้านเจ"},
            fact_key="hours",
        ))
        result = interpret_semantic_language_v1(
            "ร้านบ้านเจเปิดเมื่อไหร่",
            {"conversation_state": self.state().to_payload()},
            [{"name": "บ้านเจ"}, {"name": "สวนผัก"}],
            provider=fake,
        )
        self.assertEqual("candidate_ordinal", result.meaning["reference"]["kind"])
        self.assertEqual(1, result.meaning["reference"]["ordinal"])

    def test_10_openai_adapter_uses_responses_structured_outputs_and_no_store(self):
        provider = OpenAIResponsesSemanticProviderV1(api_key="test-key")
        request_payload = provider._request_payload(build_semantic_input_v1("ทดสอบ", {}))
        self.assertEqual(DEFAULT_OPENAI_MODEL, provider.model)
        self.assertEqual("json_schema", request_payload["text"]["format"]["type"])
        self.assertTrue(request_payload["text"]["format"]["strict"])
        self.assertFalse(request_payload["store"])
        self.assertEqual("none", request_payload["reasoning"]["effort"])
        self.assertEqual("https://api.openai.com/v1/responses", DEFAULT_OPENAI_ENDPOINT)

    def test_11_environment_defaults_to_disabled_without_api_key(self):
        with mock.patch.dict(os.environ, {"PRACHINLIFE_SEMANTIC_PROVIDER": "auto", "OPENAI_API_KEY": ""}, clear=False):
            result = interpret_semantic_language_v1("หาร้านเจ", {})
        self.assertEqual("fallback_disabled", result.status)
        self.assertFalse(result.used_model)

    def test_12_runtime_has_separate_semantic_endpoint_for_blind_evaluation(self):
        self.assertIn('def run_semantic(payload:', RUNTIME)
        self.assertIn('"/v1/semantic"', RUNTIME)
        self.assertIn("semantic_provider_health_v1()", RUNTIME)

    def test_13_runtime_language_model_feeds_semantic_resolver_before_msb(self):
        language = RUNTIME.index("interpret_semantic_language_v1(")
        resolver = RUNTIME.index("resolve_semantic_turn_v1(", language)
        decision = RUNTIME.index("run_end_to_end_real_decision_flow_v1(", resolver)
        self.assertLess(language, resolver)
        self.assertLess(resolver, decision)
        self.assertIn("language_interpretation=language_result.meaning", RUNTIME[resolver:decision])

    def test_14_phrase_specific_explanation_detector_not_added(self):
        self.assertNotIn("def _detect_explanation_request", SEMANTIC)
        self.assertIn("compatibility fallback only", SEMANTIC)

    def test_15_client_persists_semantic_state_but_not_provider_credentials(self):
        self.assertIn("language_act", JS)
        self.assertIn("semantic_criteria", JS)
        self.assertNotIn("OPENAI_API_KEY", JS)
        self.assertNotIn("Authorization", JS)

    def test_16_cache_bust(self):
        self.assertIn("generic-semantic-language-brain-v1", INDEX)

    def test_17_system_prompt_explicitly_denies_decision_authority(self):
        low = GENERIC.casefold()
        self.assertIn("never recommend, rank, score, choose, or reorder", low)
        self.assertIn("never use sponsor/provider/commercial status", low)


if __name__ == "__main__":
    unittest.main()
