"""Phase 2V.3.1 read-only diagnostics for approved create-place candidates.

This module explains which canonical places caused an approved
create_place_candidate to resolve as MATCHED/REVIEW. It never mutates either
canonical or review databases and never changes resolution/adoption policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

from .admin_drafts import AdminDraftStore
from .controlled_adoption import file_sha256
from .controlled_candidate_adoption import _candidate_observation, _draft_evidence, _latest_approved_create
from .discovery_readonly import load_canonical_places_readonly
from .discovery_resolution import canonical_observation
from .entity_resolution import EntityResolutionEngine, ResolutionOutcome

DIAGNOSTIC_POLICY_VERSION = "2V.3.1-resolution-diagnostic-v1"


@dataclass(frozen=True)
class ResolutionComparison:
    canonical_place_id: str
    canonical_name: str
    province: str | None
    latitude: float | None
    longitude: float | None
    distance_m: float | None
    outcome: str
    score: int
    signals: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class CreateCandidateResolutionDiagnostic:
    mode: str
    policy_version: str
    draft_id: str
    candidate_place_id: str
    candidate_name: str
    comparison_count: int
    relevant_count: int
    same_entity_count: int
    review_count: int
    overall_outcome: str
    overall_reason: str
    comparisons: tuple[ResolutionComparison, ...]
    canonical_hash_before: str
    canonical_hash_after: str
    canonical_unchanged: bool
    publication_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _distance_m(left, right) -> float | None:
    if left is None or right is None:
        return None
    radius_m = 6_371_008.8
    lat1, lon1, lat2, lon2 = map(
        radians,
        (left.latitude, left.longitude, right.latitude, right.longitude),
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(2 * radius_m * asin(sqrt(value)), 2)


def diagnose_approved_create_candidate_resolution(
    *, canonical_database: str | Path, draft_database: str | Path, draft_id: str
) -> CreateCandidateResolutionDiagnostic:
    canonical_database = Path(canonical_database)
    draft_database = Path(draft_database)
    before_hash = file_sha256(canonical_database)
    draft_before = file_sha256(draft_database)

    with AdminDraftStore(draft_database) as drafts:
        item = _latest_approved_create(drafts, draft_id)
        if item is None:
            raise ValueError("draft must be the latest approved create_place_candidate version")
        candidate_place_id = str(item.get("candidate_place_id") or "")
        if not candidate_place_id:
            raise ValueError("approved create candidate has no candidate_place_id")
        evidence = _draft_evidence(item)

    observation = _candidate_observation(item, evidence)
    candidate = observation.candidate
    engine = EntityResolutionEngine()
    places = tuple(sorted(load_canonical_places_readonly(canonical_database), key=lambda p: p.identity.place_id))

    same: list[ResolutionComparison] = []
    review: list[ResolutionComparison] = []
    for place in places:
        decision = engine.compare(observation, canonical_observation(place))
        if decision.outcome not in {ResolutionOutcome.SAME_ENTITY, ResolutionOutcome.REVIEW}:
            continue
        comparison = ResolutionComparison(
            canonical_place_id=place.identity.place_id,
            canonical_name=place.canonical_name,
            province=place.province,
            latitude=(place.location.latitude if place.location else None),
            longitude=(place.location.longitude if place.location else None),
            distance_m=_distance_m(candidate.location, place.location),
            outcome=decision.outcome.value,
            score=decision.score,
            signals=tuple(signal.value for signal in decision.signals),
            reason=decision.reason,
        )
        (same if decision.outcome is ResolutionOutcome.SAME_ENTITY else review).append(comparison)

    # Mirror CanonicalResolutionOrchestrator semantics exactly.
    if len(same) == 1 and not review:
        overall_outcome = "matched"
        overall_reason = "one deterministic canonical match"
    elif same or review:
        overall_outcome = "review"
        overall_reason = "ambiguous or review-required canonical match"
    else:
        overall_outcome = "new"
        overall_reason = "no canonical match"

    comparisons = tuple(sorted(
        (*same, *review),
        key=lambda x: (
            0 if x.outcome == ResolutionOutcome.SAME_ENTITY.value else 1,
            -(x.score or 0),
            x.distance_m if x.distance_m is not None else float("inf"),
            x.canonical_name.casefold(),
            x.canonical_place_id,
        ),
    ))

    after_hash = file_sha256(canonical_database)
    if file_sha256(draft_database) != draft_before:
        raise RuntimeError("diagnostic mutated draft database")

    return CreateCandidateResolutionDiagnostic(
        mode="READ_ONLY_DIAGNOSTIC",
        policy_version=DIAGNOSTIC_POLICY_VERSION,
        draft_id=draft_id,
        candidate_place_id=candidate_place_id,
        candidate_name=candidate.name,
        comparison_count=len(places),
        relevant_count=len(comparisons),
        same_entity_count=len(same),
        review_count=len(review),
        overall_outcome=overall_outcome,
        overall_reason=overall_reason,
        comparisons=comparisons,
        canonical_hash_before=before_hash,
        canonical_hash_after=after_hash,
        canonical_unchanged=before_hash == after_hash,
    )
