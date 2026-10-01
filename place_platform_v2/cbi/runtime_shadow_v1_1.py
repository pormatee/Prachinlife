from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Mapping

from .adapter_v1 import _forbidden_keys
from .pinned_runtime_v1_1 import (
    PinnedCBIRuntimeV11,
    build_pinned_cbi_v1_1,
)
from .runtime_v1_1 import SOURCE_COMMIT

CBI_RUNTIME_SHADOW_VERSION = "1.0"
CBI_RUNTIME_SHADOW_MODE = "SHADOW"
CBI_RUNTIME_SHADOW_SOURCE_COMMIT = SOURCE_COMMIT
CBI_RUNTIME_SHADOW_PRODUCTION_EFFECT = False

_MAX_STATEFUL_SESSIONS = 256


@dataclass(frozen=True)
class CBIRuntimeShadowObservationV11:
    semantic_result: Mapping[str, Any]
    next_state: Mapping[str, Any] | None
    request_id: str
    user_id: str
    session_id: str
    turn: int
    state_version: int
    stateful: bool

    runtime_version: str = "1.1.0"
    mode: str = CBI_RUNTIME_SHADOW_MODE
    shadow_only: bool = True
    production_effect: bool = False


class LocalLifeCBIRuntimeShadowV11:
    '''Pinned CBI V1.1 observer with zero decision authority.

    Only requests carrying both user_id and session_id are allowed to keep
    shadow conversation state across requests. Anonymous requests are isolated
    by request_id and never share state.
    '''

    def __init__(
        self,
        runtime: PinnedCBIRuntimeV11 | None = None,
    ) -> None:
        self._runtime = (
            runtime
            if runtime is not None
            else build_pinned_cbi_v1_1()
        )

        if self._runtime.source_commit != SOURCE_COMMIT:
            raise ValueError(
                "cbi_shadow_source_commit_mismatch"
            )

        if self._runtime.runtime_version != "1.1.0":
            raise ValueError(
                "cbi_shadow_runtime_version_mismatch"
            )

        provider = getattr(
            self._runtime.core,
            "provider_port",
            None,
        )

        if (
            provider is not None
            and bool(getattr(provider, "available", False))
        ):
            raise ValueError(
                "wave6d3_requires_provider_unavailable"
            )

        self._lock = RLock()
        self._states: OrderedDict[
            tuple[str, str],
            Mapping[str, Any],
        ] = OrderedDict()
        self._last_observation: (
            CBIRuntimeShadowObservationV11 | None
        ) = None

    @staticmethod
    def _clean_id(value: Any) -> str:
        return str(value or "").strip()[:200]

    @staticmethod
    def _context(
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        value = payload.get("context")
        return value if isinstance(value, Mapping) else {}

    def _identity(
        self,
        payload: Mapping[str, Any],
        request_id: str,
    ) -> tuple[str, str, bool]:
        context = self._context(payload)

        user_id = self._clean_id(
            payload.get("user_id")
            or context.get("user_id")
        )
        session_id = self._clean_id(
            payload.get("session_id")
            or context.get("session_id")
        )

        if user_id and session_id:
            return user_id, session_id, True

        return (
            user_id or "anonymous",
            f"request:{request_id}",
            False,
        )

    def _remember_state(
        self,
        key: tuple[str, str],
        next_state: Mapping[str, Any],
    ) -> None:
        self._states[key] = dict(next_state)
        self._states.move_to_end(key)

        while len(self._states) > _MAX_STATEFUL_SESSIONS:
            self._states.popitem(last=False)

    def observe_payload(
        self,
        payload: Mapping[str, Any],
    ) -> CBIRuntimeShadowObservationV11 | None:
        if not isinstance(payload, Mapping):
            return None

        message = payload.get("text")

        if (
            not isinstance(message, str)
            or not message.strip()
        ):
            return None

        request_id = self._clean_id(
            payload.get("request_id")
        ) or "locallife-shadow-request"

        user_id, session_id, stateful = self._identity(
            payload,
            request_id,
        )

        key = (user_id, session_id)

        with self._lock:
            previous_state = (
                self._states.get(key)
                if stateful
                else None
            )

            if previous_state is None:
                turn = 1
                state_version = 0
            else:
                turn = int(
                    previous_state.get("turn", 0)
                ) + 1
                state_version = int(
                    previous_state.get(
                        "state_version",
                        0,
                    )
                )

            result = self._runtime.core.process(
                {
                    "project_id": "locallife",
                    "user_id": user_id,
                    "session_id": session_id,
                    "request_id": request_id,
                    "turn": turn,
                    "state_version": state_version,
                    "message": message.strip(),
                },
                self._runtime.domain_pack,
                previous_state=previous_state,
            )

            if not isinstance(result, Mapping):
                raise TypeError(
                    "cbi_shadow_result_must_be_mapping"
                )

            semantic = result.get(
                "semantic_result"
            )

            if not isinstance(semantic, Mapping):
                raise TypeError(
                    "cbi_shadow_semantic_must_be_mapping"
                )

            forbidden = _forbidden_keys(semantic)

            if forbidden:
                raise ValueError(
                    "cbi_shadow_exceeds_authority:"
                    + ",".join(forbidden)
                )

            next_state = result.get("next_state")

            if (
                next_state is not None
                and not isinstance(next_state, Mapping)
            ):
                raise TypeError(
                    "cbi_shadow_next_state_must_be_mapping"
                )

            if stateful and next_state is not None:
                self._remember_state(
                    key,
                    next_state,
                )

            observation = (
                CBIRuntimeShadowObservationV11(
                    semantic_result=dict(semantic),
                    next_state=(
                        None
                        if next_state is None
                        else dict(next_state)
                    ),
                    request_id=request_id,
                    user_id=user_id,
                    session_id=session_id,
                    turn=turn,
                    state_version=state_version,
                    stateful=stateful,
                )
            )

            self._last_observation = observation
            return observation

    def last_observation(
        self,
    ) -> CBIRuntimeShadowObservationV11 | None:
        with self._lock:
            return self._last_observation

    def reset_shadow_state(self) -> None:
        with self._lock:
            self._states.clear()
            self._last_observation = None


def build_locallife_cbi_runtime_shadow_v1_1(
) -> LocalLifeCBIRuntimeShadowV11:
    return LocalLifeCBIRuntimeShadowV11()
