import sys
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from scripts.place_discovery_candidates import (
    evaluate_candidate_batch,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def build_item(
    item_id,
    title,
    *,
    tier="dedicated",
    needs_review=False,
    lat=14.05,
    lon=101.37,
):
    return {
        "id": item_id,
        "title": title,
        "location": {
            "province": "ปราจีนบุรี",
            "latitude": lat,
            "longitude": lon,
        },
        "metadata": {
            "display_tier": tier,
            "needs_review": needs_review,
        },
        "source_url":
            "https://example.com/place",
    }


def main():
    existing = [
        build_item(
            "existing-1",
            "อาหารเจ ซั่นสี่",
        )
    ]

    candidates = [
        build_item(
            "new-1",
            "ร้านอาหารเจใหม่",
        ),
        build_item(
            "new-2",
            "ร้านรอตรวจ",
            needs_review=True,
        ),
        build_item(
            "new-3",
            "อาหารเจ ซั่นสี่",
        ),
    ]

    result = evaluate_candidate_batch(
        candidates,
        existing,
    )

    check(
        result["total"] == 3,
        "batch total preserved",
    )

    check(
        len(result["accepted"]) == 1,
        "ready candidate accepted",
    )

    check(
        len(result["blocked"]) == 1,
        "review candidate blocked",
    )

    check(
        len(result["duplicates"]) == 1,
        "duplicate candidate separated",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY CANDIDATE CORE")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
