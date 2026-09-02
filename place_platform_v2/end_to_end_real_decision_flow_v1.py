"""End-to-End Real Decision Flow V1.

Deterministic consumer orchestration:
user text -> Understanding Stack -> Published Place Read Model -> Real Candidate
Mapping -> tri-state consumer gate -> DQE -> structured decision explanation.

This module is read-only. It never reads canonical places/raw evidence directly,
never writes the database, never publishes, and never calls an LLM/provider.
"""
from __future__ import annotations

from place_platform_v2.decision_context_normalization_v1 import normalize_decision_context_v1

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import GeoPoint
from .consumer_decision_contract_v1 import ConsumerDecisionRequest
from .intent_context_understanding_v1 import StructuredDecisionRequest, understand_user_request
from .publication import PublishedPlaceView
from .read_model import (
    PublishedNearbyQuery,
    PublishedPlaceRepository,
    PublishedTextQuery,
)
from .real_decision_integration_v1 import (
    RealDecisionIntegrationResult,
    evaluate_published_decision,
)


_SERVICE_MARKERS = (
    "service", "fuel", "gas", "gas_station", "fuel_station",
    "ปั๊ม", "น้ำมัน",
    "clinic", "pharmacy", "repair", "laundry",
    "บริการ", "คลินิก", "ร้านยา", "ซ่อม", "ซักรีด",
)

_CATEGORY_MARKERS: Mapping[str, tuple[str, ...]] = {
    "vegetarian": ("vegetarian", "vegan", "jay", "เจ", "มังสวิรัติ"),
    "eat": ("eat", "food", "restaurant", "cafe", "คาเฟ่", "ร้านอาหาร", "อาหาร", "vegetarian", "vegan", "jay", "เจ", "มังสวิรัติ"),
    "shopping": ("shopping", "shop", "store", "market", "supermarket", "mall", "ห้าง", "ตลาด", "ซูเปอร์"),
    "go": ("go", "travel", "attraction", "temple", "park", "เที่ยว", "ที่เที่ยว", "วัด", "สวน"),
    "service": _SERVICE_MARKERS,
}

_OBJECT_MARKERS: Mapping[str, tuple[str, ...]] = {
    "fuel_station": ("fuel", "gas", "gas_station", "fuel_station", "ปั๊ม", "น้ำมัน"),
    "restaurant": ("eat", "food", "restaurant", "cafe", "คาเฟ่", "ร้านอาหาร", "อาหาร", "vegetarian", "vegan", "jay", "เจ", "มังสวิรัติ"),
    "shop": ("shopping", "shop", "store", "market", "supermarket", "mall", "ห้าง", "ตลาด", "ซูเปอร์"),
    "destination": ("go", "travel", "attraction", "temple", "park", "เที่ยว", "ที่เที่ยว", "วัด", "สวน"),
    "service_place": _SERVICE_MARKERS,
}


@dataclass(frozen=True)
class DecisionExplanationV1:
    best_fit_candidate_id: str | None
    best_fit_name: str | None
    why_fit: tuple[str, ...]
    alternatives: tuple[str, ...]
    uncertainty_fields: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    regret_risks: tuple[str, ...]
    human_final_decision: bool


@dataclass(frozen=True)
class EndToEndRealDecisionResultV1:
    request_id: str
    status: str
    understanding: StructuredDecisionRequest
    published_candidate_ids: tuple[str, ...]
    compatible_candidate_ids: tuple[str, ...]
    decision: RealDecisionIntegrationResult | None
    explanation: DecisionExplanationV1
    needs_user_input: bool
    highest_value_question: str | None
    human_final_decision: bool = True


def _normal(value: str) -> str:
    return " ".join(str(value).casefold().split())


def _matches_any_category(place: PublishedPlaceView, markers: Sequence[str]) -> bool:
    cats = tuple(_normal(x) for x in place.categories)
    return any(any(_normal(marker) in cat for marker in markers) for cat in cats)


def _candidate_compatible(place: PublishedPlaceView, understanding: StructuredDecisionRequest) -> bool:
    if understanding.decision_object:
        markers = _OBJECT_MARKERS.get(understanding.decision_object)
        if markers:
            return _matches_any_category(place, markers)
    if understanding.category:
        markers = _CATEGORY_MARKERS.get(understanding.category)
        if markers:
            return _matches_any_category(place, markers)
    return False


def _origin_from_context(context: Mapping[str, Any] | None) -> GeoPoint | None:
    if not context:
        return None
    value = context.get("current_location")
    if value is None:
        return None
    if isinstance(value, GeoPoint):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return GeoPoint(float(value[0]), float(value[1]))
    raise ValueError("current_location must be GeoPoint or (latitude, longitude)")


def _question_for(understanding: StructuredDecisionRequest) -> str | None:
    unresolved = set(understanding.unresolved_context)
    if "current_location" in unresolved:
        return "ตอนนี้คุณอยู่บริเวณไหน เพื่อให้หาใกล้ฉันได้ถูกต้อง?"
    if understanding.category is None or understanding.decision_object is None:
        return "กำลังต้องการเลือกอะไร เช่น ร้านอาหาร ปั๊ม ร้านค้า ที่เที่ยว หรือบริการ?"
    if "location" in unresolved:
        return "ต้องการหาในจังหวัดหรือบริเวณไหน?"
    # Missing opening hours/price/etc. are system evidence gaps, not questions
    # the user should have to answer merely to hide missing data.
    return None


def _fetch_published_places(
    repository: PublishedPlaceRepository,
    understanding: StructuredDecisionRequest,
    *,
    origin: GeoPoint | None,
    location_text: str | None,
    radius_km: float,
    limit: int,
) -> tuple[PublishedPlaceView, ...]:
    if understanding.near_me and origin is not None:
        nearby = repository.search_nearby(
            PublishedNearbyQuery(
                origin=origin,
                radius_km=radius_km,
                province=understanding.province,
                limit=limit,
            )
        )
        return tuple(item.place for item in nearby)

    # A user-supplied area name is a broad text-area fallback only. It is not
    # converted into coordinates and therefore cannot become distance evidence.
    return tuple(
        repository.search_text(
            PublishedTextQuery(
                text=(location_text or "") if understanding.province is None else "",
                province=understanding.province,
                limit=limit,
            )
        )
    )


def _explain(
    decision: RealDecisionIntegrationResult | None,
    compatible: Sequence[PublishedPlaceView],
) -> DecisionExplanationV1:
    by_id = {p.place_id: p for p in compatible}
    if decision is None:
        return DecisionExplanationV1(None, None, (), (), (), (), (), True)

    best_id = decision.best_fit_candidate_id
    best_name = by_id[best_id].name if best_id in by_id else None
    why: list[str] = []
    if best_id:
        evaluated = next((x for x in decision.dqe_result.recommended if x.candidate_id == best_id), None)
        if evaluated is not None:
            why.append(f"hard_constraint_fit={evaluated.constraint_fit:.3f}")
            why.append(f"preference_fit={evaluated.preference_fit:.3f}")
            why.append(f"evidence_confidence={evaluated.evidence_confidence:.3f}")
            why.append(f"regret_risk={evaluated.regret_risk:.3f}")
    return DecisionExplanationV1(
        best_fit_candidate_id=best_id,
        best_fit_name=best_name,
        why_fit=tuple(why),
        alternatives=decision.alternative_candidate_ids,
        uncertainty_fields=decision.uncertainty_fields,
        tradeoffs=decision.tradeoffs,
        regret_risks=decision.regret_risks,
        human_final_decision=decision.human_final_decision,
    )


def run_end_to_end_real_decision_flow_v1(
    *,
    request_id: str,
    user_text: str,
    repository: PublishedPlaceRepository,
    context: Mapping[str, Any] | None = None,
    radius_km: float = 20.0,
    candidate_limit: int = 50,
    recommendation_limit: int = 3,
) -> EndToEndRealDecisionResultV1:
    raw_context = context
    context = normalize_decision_context_v1(context)
    # Conversation Gateway V1 carries explicit user-entered area text. Preserve
    # that single field even if the generic decision normalizer predates it.
    raw_location_text = None
    if raw_context and raw_context.get("location_text") is not None:
        if not isinstance(raw_context.get("location_text"), str):
            raise ValueError("location_text must be a string")
        raw_location_text = raw_context.get("location_text").strip() or None
        if raw_location_text and len(raw_location_text) > 200:
            raise ValueError("location_text too long")
    if raw_location_text:
        context = dict(context)
        context["location_text"] = raw_location_text

    """Execute the complete deterministic V1 decision path over published data."""
    if not request_id.strip():
        raise ValueError("request_id required")
    if radius_km <= 0:
        raise ValueError("radius_km must be greater than zero")
    if candidate_limit <= 0 or recommendation_limit <= 0:
        raise ValueError("limits must be greater than zero")

    understanding = understand_user_request(user_text, context=context)
    question = _question_for(understanding)

    if understanding.category is None or understanding.decision_object is None:
        explanation = _explain(None, ())
        return EndToEndRealDecisionResultV1(
            request_id=request_id,
            status="needs_user_input",
            understanding=understanding,
            published_candidate_ids=(),
            compatible_candidate_ids=(),
            decision=None,
            explanation=explanation,
            needs_user_input=True,
            highest_value_question=question,
        )

    origin = _origin_from_context(context)
    location_text = str(context.get("location_text") or "").strip() or None
    if understanding.near_me and origin is None and not location_text:
        explanation = _explain(None, ())
        return EndToEndRealDecisionResultV1(
            request_id=request_id,
            status="needs_user_input",
            understanding=understanding,
            published_candidate_ids=(),
            compatible_candidate_ids=(),
            decision=None,
            explanation=explanation,
            needs_user_input=True,
            highest_value_question=question,
        )

    published = _fetch_published_places(
        repository,
        understanding,
        origin=origin,
        location_text=location_text,
        radius_km=radius_km,
        limit=candidate_limit,
    )
    compatible = tuple(p for p in published if _candidate_compatible(p, understanding))

    consumer_request: ConsumerDecisionRequest = understanding.to_consumer_request(request_id)
    decision = evaluate_published_decision(
        consumer_request,
        compatible,
        origin=origin,
        limit=recommendation_limit,
        highest_value_question=question,
    )
    explanation = _explain(decision, compatible)

    status = decision.status
    if not compatible:
        status = "no_compatible_published_candidate"

    return EndToEndRealDecisionResultV1(
        request_id=request_id,
        status=status,
        understanding=understanding,
        published_candidate_ids=tuple(p.place_id for p in published),
        compatible_candidate_ids=tuple(p.place_id for p in compatible),
        decision=decision,
        explanation=explanation,
        needs_user_input=decision.needs_user_input,
        highest_value_question=decision.highest_value_question,
        human_final_decision=decision.human_final_decision,
    )
