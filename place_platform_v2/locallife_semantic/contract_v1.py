from __future__ import annotations
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Mapping, Optional, Tuple

CONTRACT_VERSION = "LOCALLIFE-SEMANTIC-CONTRACT-V1.1-SANDBOX"
LOCAL_CONFIDENCE_GATE = 0.62

class SemanticMode(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    LOCAL_WITH_FALLBACK = "LOCAL_WITH_FALLBACK"
    FALLBACK_DISABLED = "FALLBACK_DISABLED"

class SemanticIntent(str, Enum):
    FIND_PLACE = "FIND_PLACE"
    COMPARE_PLACES = "COMPARE_PLACES"
    DECIDE = "DECIDE"
    EXPLAIN = "EXPLAIN"
    UNKNOWN = "UNKNOWN"

class LocationKind(str, Enum):
    NEAR_ME = "NEAR_ME"
    EXPLICIT = "EXPLICIT"
    LANDMARK = "LANDMARK"
    UNSPECIFIED = "UNSPECIFIED"

class TimeKind(str, Enum):
    NOW = "NOW"
    TODAY = "TODAY"
    TOMORROW = "TOMORROW"
    UNSPECIFIED = "UNSPECIFIED"

@dataclass(frozen=True)
class SemanticEntity:
    kind: str
    text: str
    confidence: float = 1.0
    source: str = "local"

@dataclass(frozen=True)
class SemanticConstraint:
    key: str
    value: Any
    strength: str = "hard"
    confidence: float = 1.0
    source: str = "local"

@dataclass(frozen=True)
class SemanticPreference:
    key: str
    value: Any
    confidence: float = 1.0
    source: str = "local"

@dataclass(frozen=True)
class LocationIntent:
    kind: LocationKind = LocationKind.UNSPECIFIED
    text: Optional[str] = None

@dataclass(frozen=True)
class TimeContext:
    kind: TimeKind = TimeKind.UNSPECIFIED

@dataclass(frozen=True)
class SemanticResult:
    raw_text: str
    normalized_text: str
    primary_intent: SemanticIntent
    entity_mentions: Tuple[SemanticEntity, ...] = field(default_factory=tuple)
    category_hints: Tuple[str, ...] = field(default_factory=tuple)
    constraints: Tuple[SemanticConstraint, ...] = field(default_factory=tuple)
    preferences: Tuple[SemanticPreference, ...] = field(default_factory=tuple)
    location_intent: LocationIntent = field(default_factory=LocationIntent)
    time_context: TimeContext = field(default_factory=TimeContext)
    comparison_intent: bool = False
    confidence: float = 0.0
    unresolved_ambiguities: Tuple[str, ...] = field(default_factory=tuple)
    fallback_eligible: bool = False
    fallback_attempted: bool = False
    fallback_used: bool = False
    fallback_provider: Optional[str] = None
    contract_version: str = CONTRACT_VERSION

    def with_fallback_flags(self, *, attempted: bool, used: bool, provider: Optional[str]) -> "SemanticResult":
        return replace(self, fallback_attempted=attempted, fallback_used=used, fallback_provider=provider)

FORBIDDEN_AUTHORITY_FIELDS = frozenset({
    "candidate_id", "candidate_ids", "best_fit_candidate_id", "ranking_score",
    "organic_score", "recommendation", "recommended", "winner", "place_id",
    "publication_state", "canonical_write", "projection_write", "sponsor_weight",
    "sponsor", "sponsored", "rank", "score_candidate",
})

def validate_external_semantic_payload(payload: Mapping[str, Any]) -> None:
    lowered = {str(k).lower() for k in payload.keys()}
    bad = sorted(lowered & FORBIDDEN_AUTHORITY_FIELDS)
    if bad:
        raise ValueError("fallback payload contains forbidden decision/ranking authority fields: " + ",".join(bad))
