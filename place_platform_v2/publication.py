"""Publication policy and consumer-safe views for Place Platform V2.

Publication is the final explicit boundary between internal canonical data and
consumer-visible data. Discovery, verification, and canonical adoption never
publish by themselves. Publication is deterministic, policy-versioned, and
side-effect free in this packet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Mapping

from .contracts import GeoPoint
from .models import CanonicalPlace, PlaceLifecycle
from .verification import FieldVerification, VerificationOutcome


class PublicationOutcome(str, Enum):
    BLOCKED = "blocked"
    ELIGIBLE = "eligible"


@dataclass(frozen=True)
class PublicationPolicy:
    """Versioned rules for exposing a canonical place to consumers."""

    policy_version: str = "1.0-packet8"
    required_verified_fields: frozenset[str] = frozenset(
        {"canonical_name", "location", "province", "categories", "lifecycle"}
    )
    require_active_lifecycle: bool = True

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        allowed = {
            "canonical_name",
            "location",
            "address_text",
            "province",
            "categories",
            "phone",
            "website",
            "lifecycle",
        }
        unknown = self.required_verified_fields - allowed
        if unknown:
            raise ValueError(f"unknown publication fields: {sorted(unknown)}")


@dataclass(frozen=True)
class PublicationDecision:
    place_id: str
    outcome: PublicationOutcome
    policy_version: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if not self.reasons:
            raise ValueError("publication decision requires at least one reason")

    @property
    def may_publish(self) -> bool:
        return self.outcome is PublicationOutcome.ELIGIBLE


@dataclass(frozen=True)
class PublishedPlaceView:
    """Consumer-safe immutable projection of one canonical place."""

    place_id: str
    name: str
    location: GeoPoint
    province: str
    categories: tuple[str, ...]
    lifecycle: PlaceLifecycle
    address_text: str | None = None
    phone: str | None = None
    website: str | None = None
    publication_policy_version: str = ""
    published_at: datetime = datetime.min.replace(tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("published name is required")
        if not self.province.strip():
            raise ValueError("published province is required")
        if not self.categories:
            raise ValueError("published categories are required")
        if any(not item.strip() for item in self.categories):
            raise ValueError("published categories must not contain blank values")
        if self.lifecycle is not PlaceLifecycle.ACTIVE:
            raise ValueError("only active places may have a published view")
        if not self.publication_policy_version.strip():
            raise ValueError("publication_policy_version is required")
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")


def _verification_map(
    verifications: Iterable[FieldVerification],
    place_id: str,
) -> Mapping[str, FieldVerification]:
    result: dict[str, FieldVerification] = {}
    for verification in verifications:
        if verification.place_id != place_id:
            continue
        result[verification.field_name] = verification
    return result


def evaluate_publication(
    *,
    place: CanonicalPlace,
    verifications: Iterable[FieldVerification],
    policy: PublicationPolicy = PublicationPolicy(),
) -> PublicationDecision:
    """Evaluate publication eligibility without mutating or persisting anything."""

    reasons: list[str] = []

    if policy.require_active_lifecycle and place.lifecycle is not PlaceLifecycle.ACTIVE:
        reasons.append("canonical lifecycle is not active")
    if place.location is None:
        reasons.append("canonical location is missing")
    if not (place.province or "").strip():
        reasons.append("canonical province is missing")
    if not place.categories:
        reasons.append("canonical categories are missing")

    by_field = _verification_map(verifications, place.identity.place_id)
    for field_name in sorted(policy.required_verified_fields):
        verification = by_field.get(field_name)
        if verification is None:
            reasons.append(f"missing verification for {field_name}")
            continue
        if verification.outcome is not VerificationOutcome.VERIFIED:
            reasons.append(f"{field_name} is not verified")
            continue
        if verification.selected_value != getattr(place, field_name):
            reasons.append(f"{field_name} verification does not match canonical value")

    if reasons:
        return PublicationDecision(
            place_id=place.identity.place_id,
            outcome=PublicationOutcome.BLOCKED,
            policy_version=policy.policy_version,
            reasons=tuple(reasons),
        )

    return PublicationDecision(
        place_id=place.identity.place_id,
        outcome=PublicationOutcome.ELIGIBLE,
        policy_version=policy.policy_version,
        reasons=("canonical place satisfies publication policy",),
    )


def build_published_view(
    *,
    place: CanonicalPlace,
    decision: PublicationDecision,
    published_at: datetime | None = None,
) -> PublishedPlaceView:
    """Build a consumer-safe view only after an explicit eligible decision."""

    if decision.place_id != place.identity.place_id:
        raise ValueError("publication decision belongs to a different place")
    if not decision.may_publish:
        raise ValueError("blocked publication decision cannot create a published view")
    if place.location is None or place.province is None:
        raise ValueError("eligible place must have location and province")

    when = published_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("published_at must be timezone-aware")

    return PublishedPlaceView(
        place_id=place.identity.place_id,
        name=place.canonical_name,
        location=place.location,
        province=place.province,
        categories=tuple(place.categories),
        lifecycle=place.lifecycle,
        address_text=place.address_text,
        phone=place.phone,
        website=place.website,
        publication_policy_version=decision.policy_version,
        published_at=when,
    )
