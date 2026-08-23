from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

POLICY_VERSION = "7-final-local-decision-assistant-v1"
CLOSED = {"closed", "inactive", "removed", "permanently_closed"}

@dataclass(frozen=True)
class DecisionCandidate:
    place_id: str
    name: str
    categories: tuple[str, ...]
    lifecycle: str = "unknown"
    distance_km: float | None = None
    completeness: int = 0

@dataclass(frozen=True)
class DecisionResult:
    candidate: DecisionCandidate
    score: float
    reasons: tuple[str, ...]

def rank_candidates(candidates: Iterable[DecisionCandidate], *, category: str | None=None, limit: int=8) -> tuple[DecisionResult,...]:
    if limit <= 0: raise ValueError("limit must be positive")
    out=[]
    for c in candidates:
        if c.lifecycle.casefold() in CLOSED: continue
        score=float(max(0,min(c.completeness,5))*5); reasons=[]
        if c.distance_km is not None:
            if c.distance_km < 0: continue
            score += max(0,45-min(c.distance_km,30)*1.5)
            if c.distance_km <= 3: reasons.append("near_user")
            elif c.distance_km <= 10: reasons.append("short_trip")
        if c.completeness >= 3: reasons.append("useful_details")
        if category and category.casefold() in {x.casefold() for x in c.categories}: score += 12
        if not reasons: reasons.append("published_place_data")
        out.append(DecisionResult(c,score,tuple(reasons[:2])))
    out.sort(key=lambda r:(-r.score,r.candidate.name.casefold(),r.candidate.place_id))
    return tuple(out[:limit])
