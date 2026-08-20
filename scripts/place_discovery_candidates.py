from __future__ import annotations

from scripts.place_discovery_identity import (
    find_duplicates,
)

from scripts.place_discovery_merge_policy import (
    get_merge_decision,
)


def normalize_candidate_batch(
    records,
):
    return [
        item
        for item in (records or [])
        if isinstance(item, dict)
    ]


def evaluate_candidate(
    candidate,
    existing_records,
):
    duplicates = find_duplicates(
        candidate,
        existing_records,
    )

    merge = get_merge_decision(
        candidate
    )

    return {
        "candidate": candidate,
        "duplicates": duplicates,
        "merge": merge,
        "is_duplicate": bool(duplicates),
        "ready": (
            merge["ready"]
            and not duplicates
        ),
    }


def evaluate_candidate_batch(
    candidates,
    existing_records,
):
    candidates = normalize_candidate_batch(
        candidates
    )

    results = []

    accepted = []
    blocked = []
    duplicates = []

    for candidate in candidates:
        result = evaluate_candidate(
            candidate,
            existing_records,
        )

        results.append(result)

        if result["is_duplicate"]:
            duplicates.append(result)
        elif result["ready"]:
            accepted.append(result)
        else:
            blocked.append(result)

    return {
        "results": results,
        "accepted": accepted,
        "blocked": blocked,
        "duplicates": duplicates,
        "total": len(results),
    }
