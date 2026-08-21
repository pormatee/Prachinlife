"""Discovery ingestion boundary for Local Place Intelligence Platform V2.

Adapters discover source-native candidates. This module validates and
normalizes those candidates into source-neutral observations while preserving
provenance. Ingestion never creates or mutates a CanonicalPlace and never
publishes data; entity resolution and verification are later stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from .contracts import DiscoverySourceAdapter, GeoPoint, SourcePlaceCandidate, SourceRef
from .models import EvidenceKind


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _normalize_category(value: str) -> str:
    return " ".join(value.split()).casefold()


def _normalized_categories(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({_normalize_category(value) for value in values if value.strip()}))


@dataclass(frozen=True)
class DiscoveryRequest:
    """Source-neutral request passed through one discovery adapter."""

    query: str

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("discovery query is required")


@dataclass(frozen=True)
class EvidenceClaimDraft:
    """A source-backed field claim that is not yet attached to a canonical place."""

    source: SourceRef
    kind: EvidenceKind
    field_name: str
    value: Any

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("field_name is required")


@dataclass(frozen=True)
class NormalizedPlaceCandidate:
    """Validated, normalized candidate ready for entity resolution."""

    source: SourceRef
    candidate_key: str
    name: str
    location: GeoPoint | None = None
    address_text: str | None = None
    province: str | None = None
    categories: tuple[str, ...] = ()
    phone: str | None = None
    website: str | None = None
    raw_attributes: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("normalized candidate name is required")
        if len(self.candidate_key) != 64:
            raise ValueError("candidate_key must be a sha256 hex digest")


@dataclass(frozen=True)
class IngestionObservation:
    candidate: NormalizedPlaceCandidate
    claims: tuple[EvidenceClaimDraft, ...]


@dataclass(frozen=True)
class IngestionReport:
    source_name: str
    source_type: str
    query: str
    observations: tuple[IngestionObservation, ...]

    @property
    def count(self) -> int:
        return len(self.observations)


def candidate_fingerprint(
    *,
    name: str,
    location: GeoPoint | None,
    province: str | None,
) -> str:
    """Build a deterministic dedup-ready key without declaring entity identity.

    The key is a matching hint only. Entity Resolution V2 may use additional
    evidence and must not treat this fingerprint as a canonical place ID.
    """

    normalized_name = " ".join(name.split()).casefold()
    normalized_province = (_clean_optional(province) or "").casefold()
    if location is None:
        geo = ""
    else:
        geo = f"{location.latitude:.5f},{location.longitude:.5f}"
    payload = f"{normalized_name}|{normalized_province}|{geo}".encode("utf-8")
    return sha256(payload).hexdigest()


def normalize_candidate(candidate: SourcePlaceCandidate) -> NormalizedPlaceCandidate:
    name = " ".join(candidate.name.split())
    province = _clean_optional(candidate.province)
    categories = _normalized_categories(candidate.categories)

    return NormalizedPlaceCandidate(
        source=candidate.source,
        candidate_key=candidate_fingerprint(
            name=name,
            location=candidate.location,
            province=province,
        ),
        name=name,
        location=candidate.location,
        address_text=_clean_optional(candidate.address_text),
        province=province,
        categories=categories,
        phone=_clean_optional(candidate.phone),
        website=_clean_optional(candidate.website),
        raw_attributes=dict(candidate.raw_attributes),
    )


def build_claims(candidate: NormalizedPlaceCandidate) -> tuple[EvidenceClaimDraft, ...]:
    claims: list[EvidenceClaimDraft] = [
        EvidenceClaimDraft(
            source=candidate.source,
            kind=EvidenceKind.EXISTENCE,
            field_name="existence",
            value=True,
        ),
        EvidenceClaimDraft(
            source=candidate.source,
            kind=EvidenceKind.NAME,
            field_name="canonical_name",
            value=candidate.name,
        ),
    ]

    optional_claims = (
        (candidate.location, EvidenceKind.LOCATION, "location"),
        (candidate.address_text, EvidenceKind.ADDRESS, "address_text"),
        (candidate.province, EvidenceKind.ADDRESS, "province"),
        (candidate.categories or None, EvidenceKind.CATEGORY, "categories"),
        (candidate.phone, EvidenceKind.CONTACT, "phone"),
        (candidate.website, EvidenceKind.CONTACT, "website"),
    )
    for value, kind, field_name in optional_claims:
        if value is not None:
            claims.append(
                EvidenceClaimDraft(
                    source=candidate.source,
                    kind=kind,
                    field_name=field_name,
                    value=value,
                )
            )
    return tuple(claims)


class DiscoveryIngestionPipeline:
    """Validate adapter output and convert it into neutral observations."""

    def ingest(
        self,
        adapter: DiscoverySourceAdapter,
        request: DiscoveryRequest,
    ) -> IngestionReport:
        raw_candidates = tuple(adapter.discover(request.query))
        observations: list[IngestionObservation] = []

        for raw in raw_candidates:
            if raw.source.source_type != adapter.source_type:
                raise ValueError(
                    "adapter source_type does not match candidate provenance"
                )
            normalized = normalize_candidate(raw)
            observations.append(
                IngestionObservation(
                    candidate=normalized,
                    claims=build_claims(normalized),
                )
            )

        source_name = (
            observations[0].candidate.source.source_name
            if observations
            else adapter.source_type.value
        )
        return IngestionReport(
            source_name=source_name,
            source_type=adapter.source_type.value,
            query=request.query.strip(),
            observations=tuple(observations),
        )
