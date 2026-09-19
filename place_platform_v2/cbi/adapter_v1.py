from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

CBI_RUNTIME_VERSION = "1.0.0"
CBI_RUNTIME_COMMIT = "0c35f4b81bdb928939c73b2cb669f3ec3f756f51"
CBI_DOMAIN_ID = "local_life"
CBI_DOMAIN_PACK_VERSION = "1.1.0"
CBI_MODE = "SHADOW"

FORBIDDEN_AUTHORITY_FIELDS = frozenset({
    "best_fit_candidate_id",
    "candidate_id",
    "candidate_ids",
    "canonical_write",
    "organic_score",
    "place_id",
    "projection_write",
    "publication_state",
    "publication_write",
    "rank",
    "ranking_score",
    "recommendation",
    "recommended",
    "score_candidate",
    "sponsor_weight",
    "winner",
})


def _forbidden_keys(value: Any, path: str = "$") -> tuple[str, ...]:
    hits = []

    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key)
            child = f"{path}.{name}"

            if name.casefold() in FORBIDDEN_AUTHORITY_FIELDS:
                hits.append(child)

            hits.extend(_forbidden_keys(item, child))

    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            hits.extend(_forbidden_keys(item, f"{path}[{index}]"))

    return tuple(hits)


@dataclass(frozen=True)
class CBIShadowObservationV1:
    semantic_result: Mapping[str, Any]
    next_state: Mapping[str, Any] | None

    runtime_version: str = CBI_RUNTIME_VERSION
    domain_pack_version: str = CBI_DOMAIN_PACK_VERSION
    mode: str = CBI_MODE

    shadow_only: bool = True
    production_effect: bool = False


class LocalLifeCBIShadowAdapterV1:
    """Thin LocalLife adapter for injected MEasyMate CBI V1.

    Wave 6A is observation-only.
    CBI understands; LocalLife Project Brain decides.
    """

    def __init__(
        self,
        cbi_core: Any,
        domain_pack: Mapping[str, Any],
    ):
        runtime_version = str(
            getattr(cbi_core, "runtime_version", "") or ""
        )

        if runtime_version != CBI_RUNTIME_VERSION:
            raise ValueError("cbi_runtime_version_mismatch")

        if str(domain_pack.get("domain_id", "")) != CBI_DOMAIN_ID:
            raise ValueError("cbi_domain_pack_id_mismatch")

        if str(domain_pack.get("version", "")) != CBI_DOMAIN_PACK_VERSION:
            raise ValueError("cbi_domain_pack_version_mismatch")

        provider_port = getattr(cbi_core, "provider_port", None)

        if (
            provider_port is not None
            and bool(getattr(provider_port, "available", False))
        ):
            raise ValueError("cbi_shadow_requires_provider_none")

        if not callable(getattr(cbi_core, "process", None)):
            raise TypeError("cbi_core_process_required")

        self._cbi_core = cbi_core
        self._domain_pack = domain_pack

    def observe(
        self,
        *,
        user_id: str,
        session_id: str,
        request_id: str,
        turn: int,
        state_version: int,
        message: str,
        previous_state: Mapping[str, Any] | None = None,
    ) -> CBIShadowObservationV1:

        request = {
            "project_id": "locallife",
            "user_id": user_id,
            "session_id": session_id,
            "request_id": request_id,
            "turn": turn,
            "state_version": state_version,
            "message": message,
        }

        result = self._cbi_core.process(
            request,
            self._domain_pack,
            previous_state=previous_state,
        )

        if not isinstance(result, Mapping):
            raise TypeError("cbi_result_must_be_mapping")

        semantic_result = result.get("semantic_result")

        if not isinstance(semantic_result, Mapping):
            raise TypeError("cbi_semantic_result_must_be_mapping")

        forbidden = _forbidden_keys(semantic_result)

        if forbidden:
            raise ValueError(
                "cbi_semantic_result_exceeds_authority:"
                + ",".join(forbidden)
            )

        next_state = result.get("next_state")

        if next_state is not None and not isinstance(next_state, Mapping):
            raise TypeError("cbi_next_state_must_be_mapping")

        return CBIShadowObservationV1(
            semantic_result=dict(semantic_result),
            next_state=(
                None
                if next_state is None
                else dict(next_state)
            ),
        )
