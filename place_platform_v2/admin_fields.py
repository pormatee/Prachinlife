"""Admin field intake contract for Place Platform V2.

Admin input is evidence, never a direct canonical-place write.  This module is
storage/UI agnostic and deliberately side-effect free so a later Admin Web can
use exactly the same validation boundary as scripts or APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from .models import EvidenceKind, PlaceEvidence, PlaceLifecycle


class AdminFieldRisk(str, Enum):
    IDENTITY = "identity"
    LOCATION = "location"
    DESCRIPTIVE = "descriptive"
    CONTACT = "contact"


@dataclass(frozen=True)
class AdminFieldSpec:
    name: str
    evidence_kind: EvidenceKind
    risk: AdminFieldRisk
    value_type: str
    required_for_detail: bool = False


ADMIN_FIELD_SPECS: Mapping[str, AdminFieldSpec] = {
    "canonical_name": AdminFieldSpec("canonical_name", EvidenceKind.NAME, AdminFieldRisk.IDENTITY, "text"),
    "location": AdminFieldSpec("location", EvidenceKind.LOCATION, AdminFieldRisk.LOCATION, "geopoint"),
    "address_text": AdminFieldSpec("address_text", EvidenceKind.ADDRESS, AdminFieldRisk.LOCATION, "text"),
    "province": AdminFieldSpec("province", EvidenceKind.ADDRESS, AdminFieldRisk.LOCATION, "text"),
    "district": AdminFieldSpec("district", EvidenceKind.ADDRESS, AdminFieldRisk.LOCATION, "text", True),
    "subdistrict": AdminFieldSpec("subdistrict", EvidenceKind.ADDRESS, AdminFieldRisk.LOCATION, "text", True),
    "area": AdminFieldSpec("area", EvidenceKind.ADDRESS, AdminFieldRisk.LOCATION, "text", True),
    "categories": AdminFieldSpec("categories", EvidenceKind.CATEGORY, AdminFieldRisk.IDENTITY, "categories"),
    "phone": AdminFieldSpec("phone", EvidenceKind.CONTACT, AdminFieldRisk.CONTACT, "text", True),
    "website": AdminFieldSpec("website", EvidenceKind.CONTACT, AdminFieldRisk.CONTACT, "url", True),
    "opening_hours": AdminFieldSpec("opening_hours", EvidenceKind.OPENING_STATUS, AdminFieldRisk.DESCRIPTIVE, "text", True),
    "real_image": AdminFieldSpec("real_image", EvidenceKind.OTHER, AdminFieldRisk.DESCRIPTIVE, "url", True),
    "description": AdminFieldSpec("description", EvidenceKind.OTHER, AdminFieldRisk.DESCRIPTIVE, "text", True),
    "lifecycle": AdminFieldSpec("lifecycle", EvidenceKind.OPENING_STATUS, AdminFieldRisk.IDENTITY, "lifecycle"),
}

ADMIN_DETAIL_PRIORITY_FIELDS = frozenset(
    name for name, spec in ADMIN_FIELD_SPECS.items() if spec.required_for_detail
)


@dataclass(frozen=True)
class AdminEvidenceInput:
    place_id: str
    field_name: str
    value: Any
    source_name: str
    source_url: str
    source_record_id: str | None = None
    observed_at: datetime | None = None
    note: str | None = None


def _nonblank(value: Any, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"{label} is required")
    return text


def _normalize_value(spec: AdminFieldSpec, value: Any) -> Any:
    if spec.value_type == "text":
        return _nonblank(value, spec.name)
    if spec.value_type == "url":
        url = _nonblank(value, spec.name)
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError(f"{spec.name} must be an http(s) URL")
        return url
    if spec.value_type == "geopoint":
        if isinstance(value, GeoPoint):
            return value
        if isinstance(value, Mapping):
            try:
                return GeoPoint(float(value["latitude"]), float(value["longitude"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("location requires latitude and longitude") from exc
        raise ValueError("location requires GeoPoint or coordinate mapping")
    if spec.value_type == "categories":
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError("categories requires a sequence")
        normalized = tuple(sorted({_nonblank(item, "category") for item in value}))
        if not normalized:
            raise ValueError("categories must not be empty")
        return normalized
    if spec.value_type == "lifecycle":
        try:
            return value if isinstance(value, PlaceLifecycle) else PlaceLifecycle(str(value))
        except ValueError as exc:
            raise ValueError("invalid lifecycle") from exc
    raise ValueError(f"unsupported admin value type: {spec.value_type}")


def build_admin_evidence(entry: AdminEvidenceInput) -> PlaceEvidence:
    """Validate one admin edit and convert it to CANDIDATE evidence.

    A traceable source URL is mandatory.  The function cannot mutate a
    CanonicalPlace, cannot mark evidence supported/verified, and cannot publish.
    """
    spec = ADMIN_FIELD_SPECS.get(entry.field_name)
    if spec is None:
        raise ValueError("field is not allowed by admin contract")

    source_name = _nonblank(entry.source_name, "source_name")
    source_url = _nonblank(entry.source_url, "source_url")
    if not source_url.lower().startswith(("http://", "https://")):
        raise ValueError("source_url must be an http(s) URL")

    observed_at = entry.observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")

    value = _normalize_value(spec, entry.value)
    source = SourceRef(
        source_type=SourceType.MANUAL,
        source_name=source_name,
        source_record_id=entry.source_record_id,
        source_url=source_url,
        observed_at=observed_at,
    )
    metadata = {
        "intake": "admin",
        "admin_contract_version": "2S.4-v1",
        "risk": spec.risk.value,
    }
    if entry.note and entry.note.strip():
        metadata["note"] = entry.note.strip()

    return PlaceEvidence(
        place_id=entry.place_id,
        source=source,
        kind=spec.evidence_kind,
        field_name=entry.field_name,
        value=value,
        status=EvidenceStatus.CANDIDATE,
        observed_at=observed_at,
        metadata=metadata,
    )
