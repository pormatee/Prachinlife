from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .contracts import SourcePlaceCandidate, SourceRef, SourceType
from .entity_resolution import EntityResolutionEngine, ResolutionOutcome
from .ingestion import IngestionObservation, build_claims, normalize_candidate

class DiscoveryResolutionOutcome(str, Enum):
    MATCHED = "matched"
    NEW = "new"
    REVIEW = "review"

@dataclass(frozen=True)
class DiscoveryResolutionItem:
    observation: IngestionObservation
    outcome: DiscoveryResolutionOutcome
    matched_place_id: str | None
    comparison_count: int
    reason: str

@dataclass(frozen=True)
class DiscoveryResolutionReport:
    source_name: str
    source_type: str
    query: str
    items: tuple[DiscoveryResolutionItem, ...]

    @property
    def total(self):
        return len(self.items)

    @property
    def matched_count(self):
        return sum(x.outcome is DiscoveryResolutionOutcome.MATCHED for x in self.items)

    @property
    def new_count(self):
        return sum(x.outcome is DiscoveryResolutionOutcome.NEW for x in self.items)

    @property
    def review_count(self):
        return sum(x.outcome is DiscoveryResolutionOutcome.REVIEW for x in self.items)

def canonical_observation(place):
    c = normalize_candidate(SourcePlaceCandidate(
        source=SourceRef(
            SourceType.OTHER,
            "PrachinLife V2 Canonical",
            source_record_id=place.identity.place_id,
            observed_at=place.updated_at,
        ),
        name=place.canonical_name,
        location=place.location,
        address_text=place.address_text,
        province=place.province,
        categories=place.categories,
        phone=place.phone,
        website=place.website,
    ))
    return IngestionObservation(c, build_claims(c))

class CanonicalResolutionOrchestrator:
    def __init__(self, engine=None):
        self.engine = engine or EntityResolutionEngine()

    def resolve_one(self, observation, canonical_places):
        places = tuple(sorted(canonical_places, key=lambda x: x.identity.place_id))
        same = []
        review = []
        for place in places:
            decision = self.engine.compare(observation, canonical_observation(place))
            if decision.outcome is ResolutionOutcome.SAME_ENTITY:
                same.append(place.identity.place_id)
            elif decision.outcome is ResolutionOutcome.REVIEW:
                review.append(place.identity.place_id)

        if len(same) == 1 and not review:
            return DiscoveryResolutionItem(
                observation, DiscoveryResolutionOutcome.MATCHED,
                same[0], len(places), "one deterministic canonical match"
            )
        if same or review:
            return DiscoveryResolutionItem(
                observation, DiscoveryResolutionOutcome.REVIEW,
                None, len(places), "ambiguous or review-required canonical match"
            )
        return DiscoveryResolutionItem(
            observation, DiscoveryResolutionOutcome.NEW,
            None, len(places), "no canonical match"
        )

    def resolve_report(self, ingestion_report, canonical_places):
        places = tuple(canonical_places)
        observations = tuple(sorted(
            ingestion_report.observations,
            key=lambda x: (
                x.candidate.source.source_record_id or "",
                x.candidate.candidate_key,
            ),
        ))
        return DiscoveryResolutionReport(
            ingestion_report.source_name,
            ingestion_report.source_type,
            ingestion_report.query,
            tuple(self.resolve_one(x, places) for x in observations),
        )
