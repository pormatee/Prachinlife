"""Evidence aggregation and verification contracts for Place Platform V2.

This module is deliberately deterministic and side-effect free. It aggregates
field-level evidence that has already been attached to one resolved place,
measures agreement/conflict, and returns a verification assessment. It does
not mutate CanonicalPlace, change stored evidence, or publish data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable

from .contracts import EvidenceStatus, SourceType
from .models import PlaceEvidence


class VerificationOutcome(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    SUPPORTED = "supported"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class VerificationPolicy:
    """Versionable deterministic thresholds for evidence verification."""

    verified_independent_sources: int = 2
    supported_sources: int = 1

    def __post_init__(self) -> None:
        if self.supported_sources < 1:
            raise ValueError("supported_sources must be at least 1")
        if self.verified_independent_sources < self.supported_sources:
            raise ValueError(
                "verified_independent_sources must be >= supported_sources"
            )


@dataclass(frozen=True)
class ValueSupport:
    """Aggregated support for one normalized field value."""

    value: Any
    source_count: int
    evidence_count: int
    source_types: tuple[SourceType, ...]
    latest_observed_at: datetime

    def __post_init__(self) -> None:
        if self.source_count < 1 or self.evidence_count < 1:
            raise ValueError("support counts must be positive")
        if self.latest_observed_at.tzinfo is None:
            raise ValueError("latest_observed_at must be timezone-aware")


@dataclass(frozen=True)
class FieldVerification:
    place_id: str
    field_name: str
    outcome: VerificationOutcome
    selected_value: Any | None
    supports: tuple[ValueSupport, ...]
    reason: str

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("field_name is required")
        if not self.reason.strip():
            raise ValueError("verification reason is required")
        if self.outcome is VerificationOutcome.CONFLICTING and len(self.supports) < 2:
            raise ValueError("conflicting outcome requires multiple supported values")

    @property
    def may_adopt(self) -> bool:
        return self.outcome in {
            VerificationOutcome.SUPPORTED,
            VerificationOutcome.VERIFIED,
        }

    @property
    def evidence_status(self) -> EvidenceStatus:
        mapping = {
            VerificationOutcome.INSUFFICIENT_EVIDENCE: EvidenceStatus.CANDIDATE,
            VerificationOutcome.SUPPORTED: EvidenceStatus.SUPPORTED,
            VerificationOutcome.VERIFIED: EvidenceStatus.VERIFIED,
            VerificationOutcome.CONFLICTING: EvidenceStatus.CONFLICTING,
        }
        return mapping[self.outcome]


def _freeze_value(value: Any) -> Any:
    """Convert common mutable containers into deterministic hashable values."""
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(sorted((_freeze_value(item) for item in value), key=repr))
    return value


def _source_identity(evidence: PlaceEvidence) -> tuple[str, str, str]:
    """Identity for source independence; repeated observations do not inflate trust."""
    source = evidence.source
    return (
        source.source_type.value,
        source.source_name.strip().casefold(),
        (source.source_record_id or "").strip().casefold(),
    )


def _latest(values: Iterable[datetime]) -> datetime:
    return max(values, default=datetime.fromtimestamp(0, tz=timezone.utc))


def aggregate_field_evidence(
    evidence: Iterable[PlaceEvidence],
    field_name: str,
) -> tuple[ValueSupport, ...]:
    """Aggregate active evidence by value without mutating evidence state.

    Rejected/stale evidence is retained in storage but excluded from current
    verification. Candidate/supported/verified/conflicting evidence may all
    participate because their status describes prior assessment, not source truth.
    """

    groups: dict[Any, list[PlaceEvidence]] = {}
    original_values: dict[Any, Any] = {}

    for item in evidence:
        if item.field_name != field_name:
            continue
        if item.status in {EvidenceStatus.REJECTED, EvidenceStatus.STALE}:
            continue
        key = _freeze_value(item.value)
        groups.setdefault(key, []).append(item)
        original_values.setdefault(key, item.value)

    supports: list[ValueSupport] = []
    for key, items in groups.items():
        independent_sources = {_source_identity(item) for item in items}
        source_types = tuple(sorted({item.source.source_type for item in items}, key=lambda x: x.value))
        supports.append(
            ValueSupport(
                value=original_values[key],
                source_count=len(independent_sources),
                evidence_count=len(items),
                source_types=source_types,
                latest_observed_at=_latest(item.observed_at for item in items),
            )
        )

    supports.sort(
        key=lambda support: (
            -support.source_count,
            -support.evidence_count,
            -support.latest_observed_at.timestamp(),
            repr(_freeze_value(support.value)),
        )
    )
    return tuple(supports)


def verify_field(
    *,
    place_id: str,
    field_name: str,
    evidence: Iterable[PlaceEvidence],
    policy: VerificationPolicy = VerificationPolicy(),
) -> FieldVerification:
    """Return deterministic field-level verification for one resolved place."""

    relevant = tuple(item for item in evidence if item.place_id == place_id)
    supports = aggregate_field_evidence(relevant, field_name)

    if not supports:
        return FieldVerification(
            place_id=place_id,
            field_name=field_name,
            outcome=VerificationOutcome.INSUFFICIENT_EVIDENCE,
            selected_value=None,
            supports=(),
            reason="no active evidence for field",
        )

    leader = supports[0]
    if len(supports) > 1:
        runner_up = supports[1]
        # Any independently supported competing value is surfaced as conflict.
        # Verification never silently resolves contradictory source claims.
        if runner_up.source_count >= policy.supported_sources:
            return FieldVerification(
                place_id=place_id,
                field_name=field_name,
                outcome=VerificationOutcome.CONFLICTING,
                selected_value=None,
                supports=supports,
                reason="multiple active values have independent source support",
            )

    if leader.source_count >= policy.verified_independent_sources:
        return FieldVerification(
            place_id=place_id,
            field_name=field_name,
            outcome=VerificationOutcome.VERIFIED,
            selected_value=leader.value,
            supports=supports,
            reason="value confirmed by required independent sources",
        )

    if leader.source_count >= policy.supported_sources:
        return FieldVerification(
            place_id=place_id,
            field_name=field_name,
            outcome=VerificationOutcome.SUPPORTED,
            selected_value=leader.value,
            supports=supports,
            reason="value has active source support but lacks verification quorum",
        )

    return FieldVerification(
        place_id=place_id,
        field_name=field_name,
        outcome=VerificationOutcome.INSUFFICIENT_EVIDENCE,
        selected_value=None,
        supports=supports,
        reason="active evidence does not meet support threshold",
    )


class EvidenceVerificationEngine:
    """Side-effect-free wrapper for orchestration in later packets."""

    def __init__(self, policy: VerificationPolicy | None = None) -> None:
        self.policy = policy or VerificationPolicy()

    def verify_field(
        self,
        *,
        place_id: str,
        field_name: str,
        evidence: Iterable[PlaceEvidence],
    ) -> FieldVerification:
        return verify_field(
            place_id=place_id,
            field_name=field_name,
            evidence=evidence,
            policy=self.policy,
        )
