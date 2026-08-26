from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

class PublicState(str, Enum):
    VERIFIED_PUBLIC = "verified_public"
    PENDING_HUMAN_PUBLIC_LIMITED = "pending_human_public_limited"
    HIDDEN_NOT_READY = "hidden_not_ready"

@dataclass(frozen=True)
class Scope:
    province: str
    category: str

@dataclass(frozen=True)
class PlaceDecision:
    scope: Scope
    state: PublicState
    public_visible: bool
    near_me_allowed: bool
    distance_allowed: bool
    automatic_canonical: bool = False
    automatic_approval: bool = False
    automatic_publication: bool = False
    trust_policy_lowered: bool = False
    reason: str = ""

class ProvinceCategoryPipeline:
    """Province/category-agnostic publication state policy.

    The engine contains no province-specific or category-specific branching.
    Reference fixtures belong only in tests, never in production policy code.
    """

    REQUIRED_VERIFIED_FIELDS = (
        "canonical_name",
        "province",
        "categories",
        "location",
        "lifecycle",
    )

    def classify(self, scope: Scope, record: Mapping[str, Any]) -> PlaceDecision:
        ready = bool(record.get("ready_for_publication"))
        verified = bool(record.get("verified"))
        human_required = bool(record.get("human_confirmation_required"))
        human_complete = bool(record.get("human_confirmation_complete"))
        has_coords = self._has_coordinates(record)

        if ready and verified and (not human_required or human_complete) and has_coords:
            return PlaceDecision(
                scope=scope,
                state=PublicState.VERIFIED_PUBLIC,
                public_visible=True,
                near_me_allowed=True,
                distance_allowed=True,
                reason="verified_ready_coordinate_complete",
            )

        if bool(record.get("public_limited_eligible")) and human_required and not human_complete:
            return PlaceDecision(
                scope=scope,
                state=PublicState.PENDING_HUMAN_PUBLIC_LIMITED,
                public_visible=True,
                near_me_allowed=False,
                distance_allowed=False,
                reason="pending_human_confirmation",
            )

        return PlaceDecision(
            scope=scope,
            state=PublicState.HIDDEN_NOT_READY,
            public_visible=False,
            near_me_allowed=False,
            distance_allowed=False,
            reason="not_ready_fail_closed",
        )

    @staticmethod
    def _has_coordinates(record: Mapping[str, Any]) -> bool:
        lat = record.get("latitude")
        lon = record.get("longitude")
        return lat is not None and lon is not None
