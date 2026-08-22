from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from .entity_resolution import ResolutionOutcome


@dataclass(frozen=True)
class ReviewDiagnostics:
    total_review: int
    reason_counts: tuple[tuple[str, int], ...]
    sample_names: tuple[str, ...]


def classify_review_item(item) -> str:
    candidate = item.observation.candidate

    has_geo = candidate.location is not None
    has_phone = bool(candidate.phone)
    has_website = bool(candidate.website)

    if not has_geo and not has_phone and not has_website:
        return "weak_identity_no_geo_or_contact"

    if not has_geo:
        return "missing_geo"

    if not has_phone and not has_website:
        return "geo_name_only"

    return "ambiguous_multiple_signals"


def diagnose_reviews(report, sample_limit=12) -> ReviewDiagnostics:
    reviews = [
        item for item in report.items
        if item.outcome.value == "review"
    ]

    counts = Counter(
        classify_review_item(item)
        for item in reviews
    )

    samples = tuple(
        item.observation.candidate.name
        for item in reviews[:sample_limit]
    )

    return ReviewDiagnostics(
        total_review=len(reviews),
        reason_counts=tuple(sorted(counts.items())),
        sample_names=samples,
    )
