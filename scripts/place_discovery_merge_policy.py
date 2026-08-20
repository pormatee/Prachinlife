from __future__ import annotations


PRIMARY_TIERS = {
    "dedicated",
}

SECONDARY_TIERS = {
    "named_candidate",
    "option_available",
}


def has_coordinates(item):
    location = (
        item.get("location")
        or {}
    )

    return (
        isinstance(
            location.get("latitude"),
            (int, float),
        )
        and
        isinstance(
            location.get("longitude"),
            (int, float),
        )
    )


def has_source_evidence(item):
    source_url = item.get(
        "source_url"
    )

    source_ref = item.get(
        "source_ref"
    )

    return (
        (
            isinstance(source_url, str)
            and
            source_url.startswith(
                ("http://", "https://")
            )
        )
        or
        (
            isinstance(source_ref, str)
            and
            bool(source_ref.strip())
        )
    )


def get_merge_decision(item):
    metadata = (
        item.get("metadata")
        or {}
    )

    tier = metadata.get(
        "display_tier"
    )

    reasons = []

    if not item.get("title"):
        reasons.append(
            "missing_title"
        )

    if not has_coordinates(
        item
    ):
        reasons.append(
            "missing_coordinates"
        )

    if not has_source_evidence(
        item
    ):
        reasons.append(
            "missing_source_evidence"
        )

    if (
        metadata.get("needs_review")
        is True
    ):
        reasons.append(
            "needs_review"
        )

    if tier not in PRIMARY_TIERS:
        reasons.append(
            "not_primary_tier"
        )

    ready = (
        len(reasons) == 0
    )

    return {
        "ready":
            ready,
        "tier":
            tier,
        "reasons":
            reasons,
    }


def can_merge_to_primary(
    item
):
    return get_merge_decision(
        item
    )["ready"]
