from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

import place_platform_v2.locallife_api_v1 as api

from place_platform_v2.cbi.api_shadow_v1 import (
    configure_cbi_api_shadow_observer_v1,
)
from place_platform_v2.cbi.runtime_shadow_v1_1 import (
    CBI_RUNTIME_SHADOW_MODE,
    CBI_RUNTIME_SHADOW_PRODUCTION_EFFECT,
    CBI_RUNTIME_SHADOW_SOURCE_COMMIT,
    LocalLifeCBIRuntimeShadowV11,
)


class LocalLifeCBIRuntimeShadowV11Tests(
    unittest.TestCase
):
    def setUp(self):
        configure_cbi_api_shadow_observer_v1(None)
        api._CBI_RUNTIME_SHADOW_V1_1.reset_shadow_state()

    def tearDown(self):
        configure_cbi_api_shadow_observer_v1(None)
        api._CBI_RUNTIME_SHADOW_V1_1.reset_shadow_state()

    def test_runtime_shadow_identity(self):
        self.assertEqual(
            CBI_RUNTIME_SHADOW_MODE,
            "SHADOW",
        )
        self.assertFalse(
            CBI_RUNTIME_SHADOW_PRODUCTION_EFFECT
        )
        self.assertEqual(
            CBI_RUNTIME_SHADOW_SOURCE_COMMIT,
            "4957dc6db12bdf5bccd0d95bbe8b22dbef8f1d17",
        )

    def test_real_api_request_reaches_pinned_cbi(self):
        sentinel = {
            "status": "production-result"
        }

        with patch.object(
            api,
            "_run_master_brain_decision",
            return_value=sentinel,
        ):
            result = api.decision_payload({
                "request_id": "shadow-real-1",
                "text": "หาร้านเจ",
                "context": {},
            })

        self.assertIs(result, sentinel)

        observation = (
            api._CBI_RUNTIME_SHADOW_V1_1
            .last_observation()
        )

        self.assertIsNotNone(observation)
        self.assertEqual(
            observation.runtime_version,
            "1.1.0",
        )
        self.assertTrue(
            observation.shadow_only
        )
        self.assertFalse(
            observation.production_effect
        )
        self.assertEqual(
            observation.semantic_result[
                "status"
            ],
            "UNDERSTOOD",
        )
        self.assertEqual(
            observation.semantic_result[
                "slots"
            ]["category"],
            "vegetarian",
        )

    def test_shadow_does_not_change_production_result(self):
        sentinel = {
            "status": "production-only",
            "decision": {"winner": "legacy-path"},
        }

        with patch.object(
            api,
            "_run_master_brain_decision",
            return_value=sentinel,
        ):
            result = api.decision_payload({
                "request_id": "shadow-real-2",
                "text": "หาร้านกาแฟ",
                "context": {},
            })

        self.assertIs(
            result,
            sentinel,
        )

    def test_explicit_identity_keeps_shadow_state(self):
        shadow = LocalLifeCBIRuntimeShadowV11()

        first = shadow.observe_payload({
            "request_id": "r1",
            "user_id": "u1",
            "session_id": "s1",
            "text": "หาร้าน",
            "context": {},
        })

        second = shadow.observe_payload({
            "request_id": "r2",
            "user_id": "u1",
            "session_id": "s1",
            "text": "ร้านเจ",
            "context": {},
        })

        self.assertTrue(first.stateful)
        self.assertTrue(second.stateful)
        self.assertEqual(first.turn, 1)
        self.assertEqual(second.turn, 2)
        self.assertEqual(
            second.state_version,
            1,
        )

    def test_anonymous_requests_never_share_state(self):
        shadow = LocalLifeCBIRuntimeShadowV11()

        first = shadow.observe_payload({
            "request_id": "anon-1",
            "text": "หาร้าน",
            "context": {},
        })

        second = shadow.observe_payload({
            "request_id": "anon-2",
            "text": "ร้านเจ",
            "context": {},
        })

        self.assertFalse(first.stateful)
        self.assertFalse(second.stateful)
        self.assertEqual(first.turn, 1)
        self.assertEqual(second.turn, 1)
        self.assertNotEqual(
            first.session_id,
            second.session_id,
        )

    def test_wave6d3_provider_is_unavailable(self):
        shadow = LocalLifeCBIRuntimeShadowV11()

        self.assertFalse(
            shadow._runtime.core.provider_port.available
        )

    def test_protected_web_runtime_is_not_wired(self):
        from place_platform_v2 import (
            web_ai_runtime_v1 as runtime,
        )

        source = inspect.getsource(runtime)

        self.assertNotIn(
            "runtime_shadow_v1_1",
            source,
        )
        self.assertNotIn(
            "build_locallife_cbi_runtime_shadow_v1_1",
            source,
        )


if __name__ == "__main__":
    unittest.main()
