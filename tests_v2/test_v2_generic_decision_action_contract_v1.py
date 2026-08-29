from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

import place_platform_v2.locallife_api_v1 as api
from place_platform_v2.decision_action_contract_v1 import (
    ACTION_CONTRACT_VERSION,
    attach_decision_actions_v1,
    build_decision_actions_v1,
)


class GenericDecisionActionContractV1Tests(unittest.TestCase):
    def test_recommendation_generates_generic_actions(self):
        actions = build_decision_actions_v1({
            "ok": True,
            "status": "qualified_with_uncertainty",
            "decision": {
                "best_fit": {
                    "place_id": "p1",
                    "lat": 14.0,
                    "lng": 101.0,
                },
                "alternatives": [
                    {"place_id": "p2"},
                    {"place_id": "p3"},
                ],
            },
        })
        types = [action["type"] for action in actions]
        self.assertIn("OPEN_PLACE_CARD", types)
        self.assertIn("SHOW_ALTERNATIVES", types)
        self.assertIn("COMPARE_PLACES", types)
        self.assertIn("OPEN_MAP", types)

    def test_needs_user_input_emits_only_one_question(self):
        actions = build_decision_actions_v1({
            "ok": True,
            "status": "needs_user_input",
            "highest_value_question": "ต้องการหมวดอะไรครับ",
        })
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "ASK_ONE_QUESTION")
        self.assertTrue(actions[0]["requires_user_confirmation"])

    def test_location_request_requires_user_confirmation(self):
        actions = build_decision_actions_v1({
            "ok": True,
            "status": "needs_user_input",
            "uncertainties": ["distance_norm"],
        })
        self.assertEqual(actions, [{
            "type": "REQUEST_LOCATION",
            "requires_user_confirmation": True,
        }])

    def test_attach_preserves_original_payload(self):
        original = {
            "ok": True,
            "status": "qualified_with_uncertainty",
            "decision": {"best_fit": {"place_id": "p1"}},
        }
        enriched = attach_decision_actions_v1(original)
        self.assertEqual(enriched["action_contract_version"], ACTION_CONTRACT_VERSION)
        self.assertEqual(enriched["decision"], original["decision"])
        self.assertNotIn("actions", original)

    def test_action_contract_has_no_execute_or_write_authority(self):
        import place_platform_v2.decision_action_contract_v1 as contract
        source = inspect.getsource(contract).lower()
        for token in (
            "subprocess.",
            "os.system",
            "sqlite3.connect",
            "controlled_publication",
            "adopt_candidate",
        ):
            self.assertNotIn(token, source)


class LocalLifeApiActionBoundaryV1Tests(unittest.TestCase):
    def test_raw_decision_payload_still_delegates_directly_to_master_brain(self):
        payload = {"request_id": "x", "text": "หาร้านอาหาร", "context": {}}
        sentinel = {"status": "sentinel"}
        with patch.object(api, "_run_master_brain_decision", return_value=sentinel) as fn:
            self.assertIs(api.decision_payload(payload), sentinel)
            fn.assert_called_once_with(payload)

    def test_public_decision_response_attaches_actions_after_brain(self):
        payload = {"request_id": "x", "text": "หาร้านอาหาร", "context": {}}
        sentinel = {
            "status": "qualified_with_uncertainty",
            "decision": {"best_fit": {"place_id": "p1"}},
        }
        with patch.object(api, "_run_master_brain_decision", return_value=sentinel):
            result = api.decision_response_payload(payload)

        self.assertEqual(result["action_contract_version"], "v1")
        self.assertEqual(result["actions"][0]["type"], "OPEN_PLACE_CARD")
        self.assertEqual(result["actions"][0]["target"]["place_id"], "p1")

    def test_handler_uses_decision_response_payload(self):
        source = inspect.getsource(api.Handler)
        self.assertIn("decision_response_payload(payload)", source)


if __name__ == "__main__":
    unittest.main()
