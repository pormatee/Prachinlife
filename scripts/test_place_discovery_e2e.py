import sys
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.place_discovery_candidates import (
    evaluate_candidate_batch,
)
from scripts.place_discovery_verification import (
    get_verification_decision,
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
    verification_source="user_firsthand",
    coordinate_precision="exact",
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
            "verification_source": verification_source,
            "coordinate_precision": coordinate_precision,
        },
        "source_url": "https://example.com/place",
    }


def main():
    existing = [
        build_item(
            "existing-1",
            "อาหารเจเดิม",
        )
    ]

    ready = build_item(
        "candidate-1",
        "อาหารเจใหม่",
    )

    duplicate = build_item(
        "candidate-2",
        "อาหารเจเดิม",
    )

    review = build_item(
        "candidate-3",
        "ร้านรอตรวจ",
        needs_review=True,
    )

    option = build_item(
        "candidate-4",
        "ร้านมีเมนูมังสวิรัติ",
        tier="option_available",
        verification_source="osm_diet_yes",
    )

    batch = evaluate_candidate_batch(
        [
            ready,
            duplicate,
            review,
            option,
        ],
        existing,
    )

    check(
        batch["total"] == 4,
        "all candidates evaluated",
    )

    check(
        len(batch["accepted"]) == 1,
        "only verified primary candidate accepted",
    )

    check(
        len(batch["duplicates"]) == 1,
        "duplicate separated",
    )

    check(
        len(batch["blocked"]) == 2,
        "review and option candidates blocked",
    )

    verification = get_verification_decision(
        ready
    )

    check(
        verification["status"] == "verified",
        "accepted candidate independently verifies",
    )

    accepted_title = (
        batch["accepted"][0]
        ["candidate"]["title"]
    )

    check(
        accepted_title == "อาหารเจใหม่",
        "correct candidate reaches production gate",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY ENGINE V1 E2E")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
