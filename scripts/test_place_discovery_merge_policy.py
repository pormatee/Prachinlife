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

from scripts.place_discovery_merge_policy import (
    get_merge_decision,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def build_item():
    return {
        "title":
            "ร้านอาหารเจทดสอบ",
        "location": {
            "province":
                "ปราจีนบุรี",
            "latitude":
                14.05,
            "longitude":
                101.37,
        },
        "metadata": {
            "display_tier":
                "dedicated",
            "needs_review":
                False,
        },
        "source_url":
            "https://example.com/place",
    }


def main():
    item = build_item()

    result = get_merge_decision(
        item
    )

    check(
        result["ready"],
        "verified dedicated place ready",
    )

    item = build_item()
    item["location"]["latitude"] = None

    result = get_merge_decision(
        item
    )

    check(
        not result["ready"],
        "missing coordinate blocked",
    )

    check(
        "missing_coordinates"
        in result["reasons"],
        "coordinate block reason preserved",
    )

    item = build_item()
    item["metadata"][
        "needs_review"
    ] = True

    result = get_merge_decision(
        item
    )

    check(
        not result["ready"],
        "review candidate blocked",
    )

    item = build_item()
    item["metadata"][
        "display_tier"
    ] = "option_available"

    result = get_merge_decision(
        item
    )

    check(
        not result["ready"],
        "option-only place blocked from primary",
    )

    item = build_item()
    item["source_url"] = None

    result = get_merge_decision(
        item
    )

    check(
        not result["ready"],
        "missing evidence blocked",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY MERGE POLICY")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
