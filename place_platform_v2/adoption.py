"""Canonical adoption and merge policy for Place Platform V2.

Verification decides whether evidence supports a value. Adoption is a separate,
explicit boundary that decides whether that verified value may be proposed for
the canonical entity. This module never publishes data and never writes to a
repository by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import UUID, uuid4

from .contracts import GeoPoint
from .models import CanonicalPlace, PlaceLifecycle
from .verification import FieldVerification, VerificationOutcome


class AdoptionOutcome(str, Enum):
    BLOCKED = "blocked"
    NO_CHANGE = "no_change"
    PROPOSED = "proposed"


# Fields that can be changed through evidence adoption. Identity and timestamps
# are intentionally excluded from evidence-controlled mutation.
ADOPTABLE_FIELDS = frozenset(
    {
        "canonical_name",
        "location",
        "address_text",
        "province",
        "categories",
        "phone",
        "website",
        "lifecycle",
    }
)


@dataclass(frozen=True)
class AdoptionPolicy:
    """Versionable policy for deciding which verified fields may be proposed.

    High-impact identity/location/category fields require VERIFIED by default.
    Lower-risk descriptive/contact fields may be proposed from SUPPORTED
    evidence, but still require an explicit adoption/apply step.
    """

    policy_version: str = "1.0-packet7"
    verified_required_fields: frozenset[str] = frozenset(
        {"canonical_name", "location", "province", "categories", "lifecycle"}
    )

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        unknown = self.verified_required_fields - ADOPTABLE_FIELDS
        if unknown:
            raise ValueError(f"unknown verified-required fields: {sorted(unknown)}")

    def allows(self, verification: FieldVerification) -> bool:
        if verification.field_name not in ADOPTABLE_FIELDS:
            return False
        if verification.selected_value is None:
            return False
        if verification.field_name in self.verified_required_fields:
            return verification.outcome is VerificationOutcome.VERIFIED
        return verification.outcome in {
            VerificationOutcome.SUPPORTED,
            VerificationOutcome.VERIFIED,
        }


@dataclass(frozen=True)
class AdoptionProposal:
    place_id: str
    field_name: str
    outcome: AdoptionOutcome
    current_value: Any
    proposed_value: Any | None
    verification_outcome: VerificationOutcome
    evidence_ids: tuple[str, ...]
    policy_version: str
    reason: str

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("field_name is required")
        if not self.policy_version.strip() or not self.reason.strip():
            raise ValueError("policy_version and reason are required")
        if self.outcome is AdoptionOutcome.PROPOSED and self.proposed_value is None:
            raise ValueError("proposed adoption requires a proposed_value")

    @property
    def may_apply(self) -> bool:
        return self.outcome is AdoptionOutcome.PROPOSED


@dataclass(frozen=True)
class PlaceRevision:
    revision_id: str
    place_id: str
    changed_fields: tuple[str, ...]
    before_values: Mapping[str, Any]
    after_values: Mapping[str, Any]
    reason: str
    evidence_ids: tuple[str, ...]
    policy_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        try:
            UUID(self.revision_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("revision_id must be a UUID string") from exc
        if not self.changed_fields:
            raise ValueError("revision must contain at least one changed field")
        if self.created_at.tzinfo is None:
            raise ValueError("revision created_at must be timezone-aware")
        if not self.reason.strip() or not self.policy_version.strip():
            raise ValueError("revision reason and policy_version are required")


def propose_adoption(
    *,
    place: CanonicalPlace,
    verification: FieldVerification,
    policy: AdoptionPolicy = AdoptionPolicy(),
    evidence_ids: tuple[str, ...] = (),
) -> AdoptionProposal:
    """Build a side-effect-free proposal from one field verification result."""

    if verification.place_id != place.identity.place_id:
        return AdoptionProposal(
            place_id=place.identity.place_id,
            field_name=verification.field_name,
            outcome=AdoptionOutcome.BLOCKED,
            current_value=None,
            proposed_value=None,
            verification_outcome=verification.outcome,
            evidence_ids=(),
            policy_version=policy.policy_version,
            reason="verification belongs to a different place",
        )

    if verification.field_name not in ADOPTABLE_FIELDS:
        return AdoptionProposal(
            place_id=place.identity.place_id,
            field_name=verification.field_name,
            outcome=AdoptionOutcome.BLOCKED,
            current_value=None,
            proposed_value=None,
            verification_outcome=verification.outcome,
            evidence_ids=evidence_ids,
            policy_version=policy.policy_version,
            reason="field is not adoptable by canonical policy",
        )

    current_value = getattr(place, verification.field_name)
    if not policy.allows(verification):
        return AdoptionProposal(
            place_id=place.identity.place_id,
            field_name=verification.field_name,
            outcome=AdoptionOutcome.BLOCKED,
            current_value=current_value,
            proposed_value=None,
            verification_outcome=verification.outcome,
            evidence_ids=evidence_ids,
            policy_version=policy.policy_version,
            reason="verification level does not satisfy adoption policy",
        )

    proposed_value = verification.selected_value
    if current_value == proposed_value:
        return AdoptionProposal(
            place_id=place.identity.place_id,
            field_name=verification.field_name,
            outcome=AdoptionOutcome.NO_CHANGE,
            current_value=current_value,
            proposed_value=proposed_value,
            verification_outcome=verification.outcome,
            evidence_ids=evidence_ids,
            policy_version=policy.policy_version,
            reason="canonical field already equals verified value",
        )

    return AdoptionProposal(
        place_id=place.identity.place_id,
        field_name=verification.field_name,
        outcome=AdoptionOutcome.PROPOSED,
        current_value=current_value,
        proposed_value=proposed_value,
        verification_outcome=verification.outcome,
        evidence_ids=evidence_ids,
        policy_version=policy.policy_version,
        reason="verification satisfies adoption policy",
    )


def _normalize_adopted_value(field_name: str, value: Any) -> Any:
    if field_name == "categories":
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("categories adoption requires a sequence")
        return tuple(sorted({str(item).strip() for item in value if str(item).strip()}))
    if field_name == "location" and not isinstance(value, GeoPoint):
        raise ValueError("location adoption requires GeoPoint")
    if field_name == "lifecycle" and not isinstance(value, PlaceLifecycle):
        try:
            return PlaceLifecycle(str(value))
        except ValueError as exc:
            raise ValueError("invalid lifecycle adoption value") from exc
    return value


def apply_adoption(
    *,
    place: CanonicalPlace,
    proposal: AdoptionProposal,
    applied_at: datetime | None = None,
) -> tuple[CanonicalPlace, PlaceRevision]:
    """Explicitly apply one approved proposal and return immutable revision data.

    This function is deliberately not called by verification and does not save or
    publish anything. The orchestration layer must persist both outputs atomically.
    """

    if not proposal.may_apply:
        raise ValueError("only proposed adoption may be applied")
    if proposal.place_id != place.identity.place_id:
        raise ValueError("proposal belongs to a different place")
    if proposal.field_name not in ADOPTABLE_FIELDS:
        raise ValueError("proposal field is not adoptable")

    when = applied_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("applied_at must be timezone-aware")
    if when < place.updated_at:
        raise ValueError("applied_at cannot be earlier than place.updated_at")

    value = _normalize_adopted_value(proposal.field_name, proposal.proposed_value)
    updated = replace(place, **{proposal.field_name: value, "updated_at": when})
    revision = PlaceRevision(
        revision_id=str(uuid4()),
        place_id=place.identity.place_id,
        changed_fields=(proposal.field_name,),
        before_values={proposal.field_name: proposal.current_value},
        after_values={proposal.field_name: value},
        reason=proposal.reason,
        evidence_ids=proposal.evidence_ids,
        policy_version=proposal.policy_version,
        created_at=when,
    )
    return updated, revision
