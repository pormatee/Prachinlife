"""Controlled Real Pathum Decision Scenarios V1.

This harness uses Pathum-model place identities and coordinates, but any
decision-time facts (open_now, price, parking, family suitability) are explicit
scenario fixtures, not claims about the live world.

Purpose: prove the frozen Understanding -> L4 -> Presenter chain behaves
correctly on realistic Pathum decision situations without changing Brain policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .contracts import GeoPoint
from .models import PlaceLifecycle
from .publication import PublishedPlaceView
from .read_model import InMemoryPublishedPlaceRepository
from .contextual_personal_decision_v1 import (
    DecisionTimeFact,
    ContextualPersonalDecisionResult,
    run_contextual_personal_decision_v1,
)
from .real_decision_presenter_v1 import (
    DecisionPresentationV1,
    present_contextual_personal_decision_v1,
)

SCENARIO_POLICY_VERSION = "REAL-PATHUM-SCENARIOS-V1"
SCENARIO_FACT_PREFIX = "scenario:pathum-v1:"

PATHUM_LABELS = {
    "baanj": "Baan J Veggie House",
    "vegan-garden": "Vegan Garden",
    "so-vegan-aiyara": "Vegetarian by So Vegan ไอยรา",
}

def _place(pid: str, name: str, lat: float, lon: float, categories: tuple[str, ...]) -> PublishedPlaceView:
    return PublishedPlaceView(
        place_id=pid,
        name=name,
        location=GeoPoint(lat, lon),
        province="ปทุมธานี",
        categories=categories,
        lifecycle=PlaceLifecycle.ACTIVE,
        publication_policy_version=SCENARIO_POLICY_VERSION,
        published_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
    )

def build_pathum_scenario_repository() -> InMemoryPublishedPlaceRepository:
    repo=InMemoryPublishedPlaceRepository()
    # Baan J coordinate is the reviewed Pathum pilot coordinate.
    repo.upsert_published(_place("baanj", PATHUM_LABELS["baanj"], 14.076182, 100.633498, ("vegetarian","restaurant")))
    # The other coordinates are controlled scenario coordinates only; they do
    # not assert current production canonical coordinates.
    repo.upsert_published(_place("vegan-garden", PATHUM_LABELS["vegan-garden"], 14.080000, 100.640000, ("vegan","vegetarian","restaurant")))
    repo.upsert_published(_place("so-vegan-aiyara", PATHUM_LABELS["so-vegan-aiyara"], 14.090000, 100.650000, ("vegetarian","restaurant")))
    return repo

def scenario_fact(
    place_id: str,
    field: str,
    value,
    *,
    state: str = "verified",
    confidence: float = 1.0,
) -> DecisionTimeFact:
    return DecisionTimeFact(
        place_id=place_id,
        field=field,
        value=value,
        state=state,
        source_ref=f"{SCENARIO_FACT_PREFIX}{place_id}:{field}",
        observed_at="2026-08-28T19:00:00+07:00",
        confidence=confidence,
    )

@dataclass(frozen=True)
class RealPathumScenarioOutputV1:
    scenario_id: str
    decision: ContextualPersonalDecisionResult
    presentation: DecisionPresentationV1

def run_real_pathum_scenario_v1(
    *,
    scenario_id: str,
    user_text: str,
    context: Mapping | None = None,
    decision_time_facts: Iterable[DecisionTimeFact] = (),
    visited_candidate_ids: Iterable[str] = (),
    radius_km: float = 20.0,
) -> RealPathumScenarioOutputV1:
    repo=build_pathum_scenario_repository()
    result=run_contextual_personal_decision_v1(
        request_id=scenario_id,
        user_text=user_text,
        repository=repo,
        context=context,
        decision_time_facts=tuple(decision_time_facts),
        visited_candidate_ids=tuple(visited_candidate_ids),
        radius_km=radius_km,
    )
    presentation=present_contextual_personal_decision_v1(
        result,
        candidate_labels=PATHUM_LABELS,
    )
    return RealPathumScenarioOutputV1(scenario_id,result,presentation)
