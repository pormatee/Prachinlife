"""Stable V2 architecture contracts.

No discovery source is allowed to publish directly to production. Sources emit
SourcePlaceCandidate records. Later pipeline stages normalize, resolve,
verify and publish according to explicit policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class SourceType(str, Enum):
    OSM = "osm"
    WEB = "web"
    MANUAL = "manual"
    OFFICIAL = "official"
    USER = "user"
    MERCHANT = "merchant"
    PARTNER = "partner"
    OTHER = "other"


class EvidenceStatus(str, Enum):
    CANDIDATE = "candidate"
    SUPPORTED = "supported"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    STALE = "stale"
    REJECTED = "rejected"


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True)
class SourceRef:
    source_type: SourceType
    source_name: str
    source_record_id: str | None = None
    source_url: str | None = None
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")


@dataclass(frozen=True)
class SourcePlaceCandidate:
    """Source-neutral candidate emitted by every Discovery V2 adapter."""

    source: SourceRef
    name: str
    location: GeoPoint | None = None
    address_text: str | None = None
    province: str | None = None
    categories: tuple[str, ...] = ()
    phone: str | None = None
    website: str | None = None
    raw_attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("candidate name is required")
        if any(not category.strip() for category in self.categories):
            raise ValueError("categories must not contain blank values")


class DiscoverySourceAdapter(Protocol):
    """Plug-in contract for present and future discovery sources."""

    @property
    def source_type(self) -> SourceType: ...

    def discover(self, query: str) -> Sequence[SourcePlaceCandidate]: ...


@dataclass(frozen=True)
class PublishDecision:
    """Explicit publication boundary; discovery alone never implies publish."""

    status: EvidenceStatus
    publishable: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("publish decision reason is required")
        if self.publishable and self.status not in {
            EvidenceStatus.SUPPORTED,
            EvidenceStatus.VERIFIED,
        }:
            raise ValueError(
                "only supported or verified evidence may be publishable"
            )
