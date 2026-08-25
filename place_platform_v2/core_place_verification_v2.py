"""Category-agnostic verification state model for Place Platform V2.

This module separates *place existence/identity* from *location precision*.
It is intentionally side-effect free.  A verified place may be eligible for a
controlled canonical shell while still being excluded from Near Me until exact
candidate-owned coordinates are verified.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

POLICY_VERSION = "core-place-verification-v2-compat-v1"
MIN_IDENTITY_SOURCE_FAMILIES = 2

class PlaceVerificationState(str, Enum):
    VERIFIED_NEAR_ME_READY = "VERIFIED_NEAR_ME_READY"
    VERIFIED_PLACE_COORDINATE_PENDING = "VERIFIED_PLACE_COORDINATE_PENDING"
    CANDIDATE_OR_REVIEW = "CANDIDATE_OR_REVIEW"

@dataclass(frozen=True)
class CorePlaceAssessment:
    state: PlaceVerificationState
    canonical_eligible: bool
    near_me_eligible: bool
    identity_verified: bool
    coordinates_verified: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "canonical_eligible": self.canonical_eligible,
            "near_me_eligible": self.near_me_eligible,
            "identity_verified": self.identity_verified,
            "coordinates_verified": self.coordinates_verified,
            "reasons": list(self.reasons),
        }

def _families(values: Iterable[Any]) -> set[str]:
    return {str(x).strip().casefold() for x in values if str(x or "").strip()}

def evaluate_place(*, identity_outcome: str, source_families: Iterable[Any],
                   coordinate_outcome: str | None = None,
                   duplicate_risk: bool = False,
                   identity_blockers: Iterable[str] = (),
                   review_flags: Iterable[str] = ()) -> CorePlaceAssessment:
    families = _families(source_families)
    blockers = tuple(str(x) for x in identity_blockers if str(x))
    flags = tuple(str(x) for x in review_flags if str(x))
    identity_verified = (
        identity_outcome == "VERIFIED_IDENTITY"
        and len(families) >= MIN_IDENTITY_SOURCE_FAMILIES
        and not duplicate_risk
        and not blockers
    )
    coordinates_verified = coordinate_outcome == "EXACT_COORDINATES_VERIFIED"

    if not identity_verified or flags:
        reasons = blockers + flags
        if len(families) < MIN_IDENTITY_SOURCE_FAMILIES:
            reasons += ("insufficient_independent_identity_sources",)
        if duplicate_risk:
            reasons += ("canonical_duplicate_risk",)
        if identity_outcome != "VERIFIED_IDENTITY":
            reasons += ("identity_not_verified",)
        return CorePlaceAssessment(
            PlaceVerificationState.CANDIDATE_OR_REVIEW, False, False,
            identity_verified, coordinates_verified,
            tuple(dict.fromkeys(reasons)) or ("controlled_review_required",),
        )

    if coordinates_verified:
        return CorePlaceAssessment(
            PlaceVerificationState.VERIFIED_NEAR_ME_READY, True, True, True, True,
            ("verified_identity_and_exact_candidate_coordinates",),
        )

    return CorePlaceAssessment(
        PlaceVerificationState.VERIFIED_PLACE_COORDINATE_PENDING,
        True, False, True, False,
        ("verified_place_identity", "exact_candidate_coordinates_pending"),
    )
