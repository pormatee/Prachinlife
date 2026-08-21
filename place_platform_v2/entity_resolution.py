"""Deterministic entity-resolution contract for Place Platform V2.

This stage compares normalized discovery observations and produces a match
assessment only. It never merges records, mutates CanonicalPlace, changes
evidence status, or publishes data. Ambiguous matches are explicitly routed to
review instead of being silently auto-merged.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlsplit

from .ingestion import IngestionObservation, NormalizedPlaceCandidate


class ResolutionOutcome(str, Enum):
    SAME_ENTITY = "same_entity"
    REVIEW = "review"
    DISTINCT = "distinct"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ResolutionSignal(str, Enum):
    SAME_SOURCE_RECORD = "same_source_record"
    SAME_CANDIDATE_KEY = "same_candidate_key"
    SAME_PHONE = "same_phone"
    SAME_WEBSITE = "same_website"
    SAME_NAME = "same_name"
    SIMILAR_NAME = "similar_name"
    NEAR_LOCATION = "near_location"
    SAME_PROVINCE = "same_province"
    PROVINCE_CONFLICT = "province_conflict"
    FAR_LOCATION = "far_location"


@dataclass(frozen=True)
class ResolutionPolicy:
    """Deterministic thresholds; changing these requires a versioned policy."""

    near_distance_m: float = 150.0
    far_distance_m: float = 5_000.0
    similar_name_ratio: float = 0.88

    def __post_init__(self) -> None:
        if self.near_distance_m <= 0:
            raise ValueError("near_distance_m must be positive")
        if self.far_distance_m <= self.near_distance_m:
            raise ValueError("far_distance_m must exceed near_distance_m")
        if not 0.0 <= self.similar_name_ratio <= 1.0:
            raise ValueError("similar_name_ratio must be between 0 and 1")


@dataclass(frozen=True)
class ResolutionDecision:
    outcome: ResolutionOutcome
    score: int
    signals: tuple[ResolutionSignal, ...]
    reason: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("resolution score must be between 0 and 100")
        if not self.reason.strip():
            raise ValueError("resolution reason is required")

    @property
    def may_auto_link(self) -> bool:
        return self.outcome is ResolutionOutcome.SAME_ENTITY


@dataclass(frozen=True)
class ObservationPair:
    left: IngestionObservation
    right: IngestionObservation


def _compact_text(value: str | None) -> str:
    return "" if value is None else " ".join(value.split()).casefold()


def _compact_phone(value: str | None) -> str:
    if not value:
        return ""
    return "".join(character for character in value if character.isdigit())


def _website_identity(value: str | None) -> str:
    if not value:
        return ""
    candidate = value.strip()
    if not candidate:
        return ""
    parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/").casefold()
    return f"{host}{path}" if host else ""


def _distance_m(left: NormalizedPlaceCandidate, right: NormalizedPlaceCandidate) -> float | None:
    if left.location is None or right.location is None:
        return None
    radius_m = 6_371_008.8
    lat1, lon1, lat2, lon2 = map(
        radians,
        (
            left.location.latitude,
            left.location.longitude,
            right.location.latitude,
            right.location.longitude,
        ),
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * radius_m * asin(sqrt(value))


def _same_source_record(left: NormalizedPlaceCandidate, right: NormalizedPlaceCandidate) -> bool:
    left_id = left.source.source_record_id
    right_id = right.source.source_record_id
    return bool(
        left_id
        and right_id
        and left.source.source_type == right.source.source_type
        and _compact_text(left.source.source_name) == _compact_text(right.source.source_name)
        and left_id == right_id
    )


def resolve_pair(
    pair: ObservationPair,
    policy: ResolutionPolicy = ResolutionPolicy(),
) -> ResolutionDecision:
    """Assess whether two observations refer to the same real-world place.

    Strong identity signals can auto-link. Ambiguous combinations route to
    review. Geographic/province contradictions prevent silent auto-linking.
    """

    left = pair.left.candidate
    right = pair.right.candidate
    signals: list[ResolutionSignal] = []

    province_left = _compact_text(left.province)
    province_right = _compact_text(right.province)
    province_conflict = bool(
        province_left and province_right and province_left != province_right
    )
    if province_conflict:
        signals.append(ResolutionSignal.PROVINCE_CONFLICT)
    elif province_left and province_left == province_right:
        signals.append(ResolutionSignal.SAME_PROVINCE)

    distance = _distance_m(left, right)
    if distance is not None:
        if distance <= policy.near_distance_m:
            signals.append(ResolutionSignal.NEAR_LOCATION)
        elif distance >= policy.far_distance_m:
            signals.append(ResolutionSignal.FAR_LOCATION)

    if _same_source_record(left, right):
        signals.append(ResolutionSignal.SAME_SOURCE_RECORD)
        return ResolutionDecision(
            outcome=ResolutionOutcome.SAME_ENTITY,
            score=100,
            signals=tuple(signals),
            reason="same source record identity",
        )

    # candidate_key includes name/province/location, but when location is absent
    # it is only a blocking hint: common business names can legitimately repeat.
    if (
        left.candidate_key == right.candidate_key
        and left.location is not None
        and right.location is not None
    ):
        signals.append(ResolutionSignal.SAME_CANDIDATE_KEY)
        return ResolutionDecision(
            outcome=ResolutionOutcome.SAME_ENTITY,
            score=100,
            signals=tuple(signals),
            reason="identical geo-anchored deterministic candidate fingerprint",
        )

    phone_left = _compact_phone(left.phone)
    phone_right = _compact_phone(right.phone)
    same_phone = bool(phone_left and phone_left == phone_right)
    if same_phone:
        signals.append(ResolutionSignal.SAME_PHONE)

    website_left = _website_identity(left.website)
    website_right = _website_identity(right.website)
    same_website = bool(website_left and website_left == website_right)
    if same_website:
        signals.append(ResolutionSignal.SAME_WEBSITE)

    name_left = _compact_text(left.name)
    name_right = _compact_text(right.name)
    same_name = name_left == name_right
    name_ratio = SequenceMatcher(None, name_left, name_right).ratio()
    if same_name:
        signals.append(ResolutionSignal.SAME_NAME)
    elif name_ratio >= policy.similar_name_ratio:
        signals.append(ResolutionSignal.SIMILAR_NAME)

    # Contradictory geography is a safety boundary. Strong contact identity is
    # sent to review because chains/shared contact details are possible.
    if province_conflict or ResolutionSignal.FAR_LOCATION in signals:
        if same_phone or same_website:
            return ResolutionDecision(
                outcome=ResolutionOutcome.REVIEW,
                score=60,
                signals=tuple(signals),
                reason="strong identity signal conflicts with geography",
            )
        if same_name or ResolutionSignal.SIMILAR_NAME in signals:
            return ResolutionDecision(
                outcome=ResolutionOutcome.DISTINCT,
                score=0,
                signals=tuple(signals),
                reason="similar naming contradicted by geography",
            )

    # Independent strong identifiers are sufficient when geography does not
    # contradict them.
    if same_phone or same_website:
        score = 95 if same_phone and same_website else 90
        return ResolutionDecision(
            outcome=ResolutionOutcome.SAME_ENTITY,
            score=score,
            signals=tuple(signals),
            reason="matching strong contact identity",
        )

    if same_name and ResolutionSignal.NEAR_LOCATION in signals:
        return ResolutionDecision(
            outcome=ResolutionOutcome.SAME_ENTITY,
            score=90,
            signals=tuple(signals),
            reason="same normalized name within near-distance threshold",
        )

    if ResolutionSignal.SIMILAR_NAME in signals and ResolutionSignal.NEAR_LOCATION in signals:
        return ResolutionDecision(
            outcome=ResolutionOutcome.REVIEW,
            score=70,
            signals=tuple(signals),
            reason="similar name and nearby location require review",
        )

    if same_name:
        return ResolutionDecision(
            outcome=ResolutionOutcome.REVIEW,
            score=55,
            signals=tuple(signals),
            reason="same name without enough independent location/contact evidence",
        )

    if ResolutionSignal.NEAR_LOCATION in signals:
        return ResolutionDecision(
            outcome=ResolutionOutcome.REVIEW,
            score=40,
            signals=tuple(signals),
            reason="nearby observations lack sufficient identity agreement",
        )

    return ResolutionDecision(
        outcome=ResolutionOutcome.INSUFFICIENT_EVIDENCE,
        score=0,
        signals=tuple(signals),
        reason="insufficient deterministic evidence to resolve entity identity",
    )


class EntityResolutionEngine:
    """Side-effect-free engine wrapper for future orchestration."""

    def __init__(self, policy: ResolutionPolicy | None = None) -> None:
        self.policy = policy or ResolutionPolicy()

    def compare(
        self,
        left: IngestionObservation,
        right: IngestionObservation,
    ) -> ResolutionDecision:
        return resolve_pair(ObservationPair(left=left, right=right), self.policy)
