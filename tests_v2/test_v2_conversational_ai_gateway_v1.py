
from pathlib import Path
import unittest

from place_platform_v2.intent_context_understanding_v1 import understand_user_request
from place_platform_v2.end_to_end_real_decision_flow_v1 import _fetch_published_places


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class _CaptureRepo:
    def __init__(self):
        self.text_queries = []
        self.nearby_queries = []

    def search_text(self, query):
        self.text_queries.append(query)
        return ()

    def search_nearby(self, query):
        self.nearby_queries.append(query)
        return ()


class TestConversationalAiGatewayV1(unittest.TestCase):
    def test_01_web_sends_structured_context(self):
        self.assertIn("context: decisionContextPayload()", JS)
        self.assertIn("robotAssistConversationContext.current_location", JS)
        self.assertIn("robotAssistConversationContext.location_text", JS)

    def test_02_device_location_is_requested_only_after_brain_reports_missing_current_location(self):
        self.assertIn('unresolvedContextFields(result).includes("current_location")', JS)
        self.assertIn("navigator.geolocation.getCurrentPosition", JS)
        self.assertIn('text: decisionText', JS)

    def test_03_gateway_does_not_contain_ranking_authority(self):
        start = JS.index("function decisionContextPayload()")
        end = JS.index("function placeId(", start)
        block = JS[start:end]
        for forbidden in (
            "best_fit_candidate_id",
            "alternative_candidate_ids",
            "ranking",
            "sponsor",
            "candidate_ids",
        ):
            self.assertNotIn(forbidden, block)

    def test_04_location_followup_becomes_structured_context_not_free_text(self):
        self.assertIn('robotAssistPendingContextField === "current_location"', JS)
        self.assertIn('robotAssistConversationContext.location_text = value', JS)
        self.assertIn(
            "pendingWasStructured\n            ? robotAssistPendingBaseQuery",
            JS,
        )

    def test_05_user_area_text_satisfies_location_clarification_without_fabricating_coordinates(self):
        understood = understand_user_request(
            "หาร้านเจใกล้ฉัน",
            context={"location_text": "รังสิต"},
        )
        self.assertTrue(understood.near_me)
        self.assertNotIn("current_location", understood.unresolved_context)
        self.assertEqual("รังสิต", understood.inferred_context.get("location_text"))
        self.assertNotIn("current_location", understood.inferred_context)

    def test_06_missing_location_still_requires_clarification(self):
        understood = understand_user_request("หาร้านเจใกล้ฉัน", context={})
        self.assertIn("current_location", understood.unresolved_context)

    def test_07_area_text_is_broad_search_not_nearby_distance_search(self):
        understood = understand_user_request(
            "หาร้านเจใกล้ฉัน",
            context={"location_text": "รังสิต"},
        )
        repo = _CaptureRepo()
        result = _fetch_published_places(
            repo,
            understood,
            origin=None,
            location_text="รังสิต",
            radius_km=20.0,
            limit=50,
        )
        self.assertEqual((), result)
        self.assertEqual(0, len(repo.nearby_queries))
        self.assertEqual(1, len(repo.text_queries))
        self.assertEqual("รังสิต", repo.text_queries[0].text)

    def test_08_exact_device_coordinates_use_nearby_path(self):
        from place_platform_v2.contracts import GeoPoint

        understood = understand_user_request(
            "หาร้านเจใกล้ฉัน",
            context={"current_location": [14.0, 100.0]},
        )
        repo = _CaptureRepo()
        _fetch_published_places(
            repo,
            understood,
            origin=GeoPoint(14.0, 100.0),
            location_text=None,
            radius_km=20.0,
            limit=50,
        )
        self.assertEqual(1, len(repo.nearby_queries))
        self.assertEqual(0, len(repo.text_queries))

    def test_09_cache_bust_preserves_previous_contract_and_adds_gateway(self):
        self.assertIn(
            "ai-assistant-persistent-chat-ux-v3-conversational-gateway-v1",
            INDEX,
        )

    def test_10_location_text_validation(self):
        with self.assertRaises(ValueError):
            understand_user_request(
                "หาร้านเจใกล้ฉัน",
                context={"location_text": 123},
            )
        with self.assertRaises(ValueError):
            understand_user_request(
                "หาร้านเจใกล้ฉัน",
                context={"location_text": "x" * 201},
            )


    def test_11_contextual_flow_forwards_location_text_to_shared_fetch(self):
        from place_platform_v2.contextual_personal_decision_v1 import (
            run_contextual_personal_decision_v1,
        )

        repo = _CaptureRepo()
        result = run_contextual_personal_decision_v1(
            request_id="gateway-contextual-location-text",
            user_text="หาร้านเจใกล้ฉัน",
            repository=repo,
            context={"location_text": "รังสิต"},
        )
        self.assertEqual(0, len(repo.nearby_queries))
        self.assertEqual(1, len(repo.text_queries))
        self.assertEqual("รังสิต", repo.text_queries[0].text)
        self.assertNotEqual("needs_user_input", result.status)


if __name__ == "__main__":
    unittest.main()
