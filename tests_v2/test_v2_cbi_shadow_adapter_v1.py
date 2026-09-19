from __future__ import annotations

from pathlib import Path
import unittest

from place_platform_v2.cbi.adapter_v1 import (
    CBI_DOMAIN_PACK_VERSION,
    CBI_MODE,
    CBI_RUNTIME_COMMIT,
    CBI_RUNTIME_VERSION,
    LocalLifeCBIShadowAdapterV1,
)


class _Provider:
    def __init__(self, available=False):
        self.available = available


class _FakeCBI:
    runtime_version = CBI_RUNTIME_VERSION

    def __init__(
        self,
        *,
        provider_available=False,
        semantic_result=None,
    ):
        self.provider_port = _Provider(provider_available)

        self.semantic_result = semantic_result or {
            "status": "UNDERSTOOD",
            "intent": {
                "name": "search_place",
                "domain": "local_life",
            },
            "slots": {
                "category": "vegetarian",
            },
            "confidence": {
                "band": "HIGH",
            },
        }

        self.last_request = None
        self.last_previous_state = None

    def process(
        self,
        request,
        domain_pack,
        previous_state=None,
    ):
        self.last_request = dict(request)
        self.last_previous_state = previous_state

        return {
            "semantic_result": self.semantic_result,
            "next_state": {
                "project_id": request["project_id"],
                "user_id": request["user_id"],
                "session_id": request["session_id"],
                "turn": request["turn"],
                "state_version": (
                    request["state_version"] + 1
                ),
            },
        }


def _pack():
    return {
        "domain_id": "local_life",
        "version": CBI_DOMAIN_PACK_VERSION,
    }


class LocalLifeCBIShadowAdapterV1Tests(unittest.TestCase):

    def test_frozen_runtime_pin(self):
        self.assertEqual(CBI_RUNTIME_VERSION, "1.0.0")
        self.assertEqual(
            CBI_RUNTIME_COMMIT,
            "0c35f4b81bdb928939c73b2cb669f3ec3f756f51",
        )
        self.assertEqual(
            CBI_DOMAIN_PACK_VERSION,
            "1.1.0",
        )
        self.assertEqual(CBI_MODE, "SHADOW")

    def test_shadow_observation_has_no_production_effect(self):
        core = _FakeCBI()
        adapter = LocalLifeCBIShadowAdapterV1(
            core,
            _pack(),
        )

        result = adapter.observe(
            user_id="u1",
            session_id="s1",
            request_id="r1",
            turn=1,
            state_version=0,
            message="หาร้านเจ",
        )

        self.assertTrue(result.shadow_only)
        self.assertFalse(result.production_effect)

        self.assertEqual(
            core.last_request["project_id"],
            "locallife",
        )

    def test_previous_state_is_forwarded(self):
        core = _FakeCBI()

        adapter = LocalLifeCBIShadowAdapterV1(
            core,
            _pack(),
        )

        previous = {
            "project_id": "locallife",
            "user_id": "u1",
            "session_id": "s1",
            "turn": 1,
            "state_version": 1,
        }

        adapter.observe(
            user_id="u1",
            session_id="s1",
            request_id="r2",
            turn=2,
            state_version=1,
            message="ร้านแรก",
            previous_state=previous,
        )

        self.assertIs(
            core.last_previous_state,
            previous,
        )

    def test_external_provider_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "provider_none",
        ):
            LocalLifeCBIShadowAdapterV1(
                _FakeCBI(
                    provider_available=True
                ),
                _pack(),
            )

    def test_decision_authority_is_rejected(self):
        core = _FakeCBI(
            semantic_result={
                "status": "UNDERSTOOD",
                "intent": {
                    "name": "search_place",
                },
                "winner": "place-1",
            }
        )

        adapter = LocalLifeCBIShadowAdapterV1(
            core,
            _pack(),
        )

        with self.assertRaisesRegex(
            ValueError,
            "exceeds_authority",
        ):
            adapter.observe(
                user_id="u1",
                session_id="s1",
                request_id="r1",
                turn=1,
                state_version=0,
                message="หาร้าน",
            )

    def test_wave6a_does_not_modify_web_runtime(self):
        root = Path(__file__).resolve().parents[1]

        runtime = (
            root
            / "place_platform_v2"
            / "web_ai_runtime_v1.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            "LocalLifeCBIShadowAdapterV1",
            runtime,
        )

        self.assertNotIn(
            "place_platform_v2.cbi",
            runtime,
        )


if __name__ == "__main__":
    unittest.main()
