"""Prachinburi Data Expansion Intake V1.

W1.0 is a side-effect-free targeting and intake-triage layer. It does not
write Canonical, create evidence rows, change lifecycle, or publish data.

The existing Place Platform V2 verification/adoption/publication policies
remain authoritative after intake.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .contracts import SourcePlaceCandidate


POLICY_VERSION = "PRACHINBURI-EXPANSION-INTAKE-V1"
TARGET_PROVINCE = "ปราจีนบุรี"


@dataclass(frozen=True)
class ExpansionTarget:
    category_code: str
    audited_baseline: int
    target_floor: int
    priority: int
    rationale: str

    def __post_init__(self) -> None:
        if not self.category_code.strip():
            raise ValueError("category_code is required")
        if self.audited_baseline < 0:
            raise ValueError("audited_baseline must be >= 0")
        if self.target_floor < self.audited_baseline:
            raise ValueError("target_floor must be >= audited_baseline")
        if self.priority < 1:
            raise ValueError("priority must be >= 1")
        if not self.rationale.strip():
            raise ValueError("rationale is required")

    @property
    def gap(self) -> int:
        return self.target_floor - self.audited_baseline


# These are coverage targets, never publication quotas. A place counts toward a
# target only after it passes the normal verification/adoption/publication path.
_TARGETS = MappingProxyType(
    {
        "restaurant": ExpansionTarget(
            "restaurant", 30, 60, 1,
            "high everyday usefulness; current coverage is modest",
        ),
        "cafe": ExpansionTarget(
            "cafe", 25, 45, 2,
            "high browse/filter usefulness; current coverage is modest",
        ),
        "vegetarian": ExpansionTarget(
            "vegetarian", 2, 15, 1,
            "high-value LocalLife vertical with very low current coverage",
        ),
        "attraction": ExpansionTarget(
            "attraction", 5, 20, 2,
            "tourism coverage is thin and useful for local discovery",
        ),
        "nature": ExpansionTarget(
            "nature", 1, 10, 2,
            "nature/local outing coverage is very thin",
        ),
        "park": ExpansionTarget(
            "park", 5, 15, 3,
            "supports leisure/family browsing and geographic coverage",
        ),
        "clinic": ExpansionTarget(
            "clinic", 2, 10, 2,
            "important local service category with very low coverage",
        ),
        "pharmacy": ExpansionTarget(
            "pharmacy", 1, 10, 2,
            "important local service category with very low coverage",
        ),
    }
)


class CandidateOrigin(str, Enum):
    DISCOVERY_ENGINE = "discovery_engine"
    LEGACY_PRESENTATION = "legacy_presentation"


class IntakeOutcome(str, Enum):
    ELIGIBLE_FOR_RESOLUTION = "eligible_for_resolution"
    HOLD_FOR_ENRICHMENT = "hold_for_enrichment"
    REJECT_OUT_OF_SCOPE = "reject_out_of_scope"
    REJECT_LEGACY_PRESENTATION = "reject_legacy_presentation"


@dataclass(frozen=True)
class IntakeAssessment:
    outcome: IntakeOutcome
    reason: str
    matched_target_categories: tuple[str, ...] = ()
    near_me_ready: bool = False
    policy_version: str = POLICY_VERSION

    @property
    def may_enter_entity_resolution(self) -> bool:
        return self.outcome is IntakeOutcome.ELIGIBLE_FOR_RESOLUTION


def expansion_targets() -> Mapping[str, ExpansionTarget]:
    return _TARGETS


def target_gap(category_code: str) -> int:
    target = _TARGETS.get(category_code.strip().casefold())
    if target is None:
        return 0
    return target.gap


def prioritized_target_codes() -> tuple[str, ...]:
    return tuple(
        item.category_code
        for item in sorted(
            _TARGETS.values(),
            key=lambda x: (x.priority, -x.gap, x.category_code),
        )
    )


def _clean(value: str | None) -> str:
    return " ".join(str(value or "").split()).strip()


def _traceable(candidate: SourcePlaceCandidate) -> bool:
    source = candidate.source
    return bool(_clean(source.source_record_id) or _clean(source.source_url))


def assess_candidate(
    candidate: SourcePlaceCandidate,
    *,
    origin: CandidateOrigin = CandidateOrigin.DISCOVERY_ENGINE,
) -> IntakeAssessment:
    """Triage one source candidate before entity resolution.

    Eligible does not mean verified, canonical, active, or publishable.
    """

    if origin is CandidateOrigin.LEGACY_PRESENTATION:
        return IntakeAssessment(
            IntakeOutcome.REJECT_LEGACY_PRESENTATION,
            "legacy Published presentation data is not admissible as new evidence",
        )

    province = _clean(candidate.province)
    if province != TARGET_PROVINCE:
        return IntakeAssessment(
            IntakeOutcome.REJECT_OUT_OF_SCOPE,
            "candidate is outside the W1 Prachinburi expansion scope",
        )

    normalized_categories = tuple(
        dict.fromkeys(
            _clean(category).casefold()
            for category in candidate.categories
            if _clean(category)
        )
    )
    matched = tuple(category for category in normalized_categories if category in _TARGETS)
    if not matched:
        return IntakeAssessment(
            IntakeOutcome.REJECT_OUT_OF_SCOPE,
            "candidate does not match a W1 target category",
        )

    if not _traceable(candidate):
        return IntakeAssessment(
            IntakeOutcome.HOLD_FOR_ENRICHMENT,
            "candidate source must provide source_record_id or source_url",
            matched_target_categories=matched,
            near_me_ready=candidate.location is not None,
        )

    if candidate.location is None:
        return IntakeAssessment(
            IntakeOutcome.HOLD_FOR_ENRICHMENT,
            "coordinates are required before W1 near-me capable resolution",
            matched_target_categories=matched,
            near_me_ready=False,
        )

    return IntakeAssessment(
        IntakeOutcome.ELIGIBLE_FOR_RESOLUTION,
        "candidate is in scope and traceable; continue to entity resolution",
        matched_target_categories=matched,
        near_me_ready=True,
    )


NEW_DATA_REQUIRED_PATH = (
    "source_candidate",
    "intake_triage",
    "entity_resolution_dedup",
    "field_evidence",
    "verification",
    "adoption",
    "canonical",
    "publication_gate",
    "published_projection",
)

