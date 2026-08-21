"""Canonical domain model for Local Place Intelligence Platform V2.

The domain model is intentionally storage-agnostic. A Place represents one
canonical real-world entity. Evidence records preserve field-level claims and
provenance without overwriting the canonical entity directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4

from .contracts import EvidenceStatus, GeoPoint, SourceRef


class PlaceLifecycle(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class EvidenceKind(str, Enum):
    EXISTENCE = "existence"
    NAME = "name"
    LOCATION = "location"
    ADDRESS = "address"
    CATEGORY = "category"
    CONTACT = "contact"
    OPENING_STATUS = "opening_status"
    OTHER = "other"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{field_name} must be a UUID string") from exc


@dataclass(frozen=True)
class PlaceIdentity:
    """Stable identifier for one canonical place across all consumers."""

    place_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        _validate_uuid(self.place_id, "place_id")


@dataclass(frozen=True)
class PlaceEvidence:
    """One source-backed claim about one canonical place.

    Evidence is append-oriented and does not mutate canonical fields by itself.
    Verification/publication policy may later decide whether a claim is adopted.
    """

    place_id: str
    source: SourceRef
    kind: EvidenceKind
    field_name: str
    value: Any
    status: EvidenceStatus = EvidenceStatus.CANDIDATE
    evidence_id: str = field(default_factory=lambda: str(uuid4()))
    observed_at: datetime = field(default_factory=_utcnow)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_uuid(self.evidence_id, "evidence_id")
        _validate_uuid(self.place_id, "place_id")
        if not self.field_name.strip():
            raise ValueError("field_name is required")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")


@dataclass(frozen=True)
class CanonicalPlace:
    """Storage-neutral canonical representation of a real-world place."""

    identity: PlaceIdentity
    canonical_name: str
    location: GeoPoint | None = None
    address_text: str | None = None
    province: str | None = None
    categories: tuple[str, ...] = ()
    phone: str | None = None
    website: str | None = None
    lifecycle: PlaceLifecycle = PlaceLifecycle.UNKNOWN
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.canonical_name.strip():
            raise ValueError("canonical_name is required")
        if any(not category.strip() for category in self.categories):
            raise ValueError("categories must not contain blank values")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("place timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
