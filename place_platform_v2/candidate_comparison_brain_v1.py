"""Candidate Comparison Brain V1.

Re-evaluates only candidate identities previously produced by MSB/DQE.
The conversational layer supplies intent/context but never scores, sorts,
or selects A/B/C. Ranking remains inside evaluate_published_decision (DQE).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from .consumer_decision_contract_v1 import ConsumerCondition
from .contracts import GeoPoint
from .intent_context_understanding_v1 import StructuredDecisionRequest, understand_user_request
from .real_decision_integration_v1 import RealDecisionIntegrationResult, evaluate_published_decision


@dataclass(frozen=True)
class CandidateComparisonBrainResultV1:
    understanding: StructuredDecisionRequest
    decision: RealDecisionIntegrationResult | None
    candidate_ids: tuple[str, ...]
    criterion: str
    needs_location: bool = False


def _origin_from_context(context: Mapping[str, Any] | None) -> GeoPoint | None:
    value = (context or {}).get("current_location")
    if value is None:
        return None
    if isinstance(value, GeoPoint):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return GeoPoint(float(value[0]), float(value[1]))
    raise ValueError("current_location must be GeoPoint or (latitude, longitude)")


def evaluate_prior_candidate_comparison_v1(
    *,
    request_id: str,
    effective_text: str,
    candidate_ids: tuple[str, ...],
    criterion: str,
    repository: Any,
    context: Mapping[str, Any] | None,
    recommendation_limit: int = 3,
) -> CandidateComparisonBrainResultV1:
    if criterion not in {"overall", "distance"}:
        raise ValueError("unsupported comparison criterion")
    if len(candidate_ids) < 2:
        raise ValueError("comparison requires at least two prior candidates")

    places = []
    getter = getattr(repository, "get_published", None)
    if not callable(getter):
        raise ValueError("published repository does not support get_published")
    for candidate_id in candidate_ids:
        place = getter(candidate_id)
        if place is not None:
            places.append(place)

    understanding = understand_user_request(effective_text, context=context)
    origin = _origin_from_context(context)
    if (criterion == "distance" or understanding.near_me) and origin is None:
        return CandidateComparisonBrainResultV1(
            understanding=understanding,
            decision=None,
            candidate_ids=tuple(p.place_id for p in places),
            criterion=criterion,
            needs_location=True,
        )

    request = understanding.to_consumer_request(request_id)
    if criterion == "distance":
        # Semantic interpretation adds the user's criterion; DQE still owns
        # scoring/ranking. No manual distance sort is performed here.
        preferences = tuple(p for p in request.preferences if p.key != "distance_km")
        preferences += (
            ConsumerCondition(
                "distance_km",
                None,
                strength="soft",
                weight=2.0,
                source="user",
                operator="lte",
            ),
        )
        request = replace(request, preferences=preferences)

    decision = evaluate_published_decision(
        request,
        tuple(places),
        origin=origin,
        limit=min(max(int(recommendation_limit), 1), len(places)),
        highest_value_question=None,
    )
    return CandidateComparisonBrainResultV1(
        understanding=understanding,
        decision=decision,
        candidate_ids=tuple(p.place_id for p in places),
        criterion=criterion,
        needs_location=False,
    )
