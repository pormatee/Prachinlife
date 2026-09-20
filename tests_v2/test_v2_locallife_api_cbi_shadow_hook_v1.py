from __future__ import annotations

import unittest
from unittest.mock import patch

import place_platform_v2.locallife_api_v1 as api

from place_platform_v2.cbi.api_shadow_v1 import (
    CBI_API_SHADOW_HOOK_VERSION,
    CBI_API_SHADOW_MODE,
    cbi_api_shadow_enabled_v1,
    configure_cbi_api_shadow_observer_v1,
)


class LocalLifeAPICBIShadowHookV1Tests(unittest.TestCase):
    def tearDown(self):
        configure_cbi_api_shadow_observer_v1(None)

    def test_shadow_contract_identity(self):
        self.assertEqual(
            CBI_API_SHADOW_HOOK_VERSION,
            "1.0",
        )
        self.assertEqual(
            CBI_API_SHADOW_MODE,
            "SHADOW",
        )

    def test_disabled_by_default(self):
        configure_cbi_api_shadow_observer_v1(None)
        self.assertFalse(
            cbi_api_shadow_enabled_v1()
        )

    def test_decision_request_is_observed(self):
        seen = []

        configure_cbi_api_shadow_observer_v1(
            lambda payload: seen.append(dict(payload))
        )

        payload = {
            "request_id": "shadow-r1",
            "text": "หาร้านเจ",
            "context": {},
        }

        sentinel = {
            "status": "production-result"
        }

        with patch.object(
            api,
            "_run_master_brain_decision",
            return_value=sentinel,
        ) as decision:
            result = api.decision_payload(payload)

        self.assertIs(result, sentinel)
        self.assertEqual(seen, [payload])
        decision.assert_called_once_with(payload)

    def test_shadow_return_value_cannot_replace_decision(self):
        configure_cbi_api_shadow_observer_v1(
            lambda payload: {
                "winner": "shadow-must-not-win"
            }
        )

        payload = {
            "request_id": "shadow-r2",
            "text": "หาร้านกาแฟ",
            "context": {},
        }

        sentinel = {
            "status": "production-only"
        }

        with patch.object(
            api,
            "_run_master_brain_decision",
            return_value=sentinel,
        ):
            result = api.decision_payload(payload)

        self.assertIs(result, sentinel)
        self.assertNotIn("winner", result)

    def test_shadow_exception_does_not_block_production(self):
        def broken(_payload):
            raise RuntimeError("shadow failure")

        configure_cbi_api_shadow_observer_v1(
            broken
        )

        payload = {
            "request_id": "shadow-r3",
            "text": "หาร้านอาหาร",
            "context": {},
        }

        sentinel = {
            "status": "still-production"
        }

        with patch.object(
            api,
            "_run_master_brain_decision",
            return_value=sentinel,
        ) as decision:
            result = api.decision_payload(payload)

        self.assertIs(result, sentinel)
        decision.assert_called_once_with(payload)

    def test_non_object_still_fails_existing_contract(self):
        configure_cbi_api_shadow_observer_v1(
            lambda payload: self.fail(
                "observer must not receive invalid payload"
            )
        )

        with self.assertRaises(ValueError):
            api.decision_payload([])

    def test_no_shadow_data_added_to_response(self):
        configure_cbi_api_shadow_observer_v1(
            lambda payload: {
                "semantic_result": {
                    "intent": {
                        "name": "search_place"
                    }
                }
            }
        )

        sentinel = {
            "status": "production",
            "decision": {"x": 1},
        }

        with patch.object(
            api,
            "_run_master_brain_decision",
            return_value=sentinel,
        ):
            result = api.decision_payload({
                "request_id": "shadow-r4",
                "text": "หาร้าน",
                "context": {},
            })

        self.assertEqual(result, sentinel)
        self.assertNotIn("cbi", result)
        self.assertNotIn("shadow", result)


if __name__ == "__main__":
    unittest.main()
