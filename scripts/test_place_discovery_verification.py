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

from scripts.place_discovery_verification import (
    calculate_confidence,
    get_verification_decision,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def build_item():
    return {
        "title":
            "อาหารเจทดสอบ",
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
            "verification_source":
                "user_firsthand",
            "coordinate_precision":
                "exact",
        },
        "source_url":
            "https://example.com/place",
    }


def main():

    strong = build_item()

    result = (
        calculate_confidence(
            strong
        )
    )

    check(
        result["score"] >= 75,
        "strong evidence receives high score",
    )

    decision = (
        get_verification_decision(
            strong
        )
    )

    check(
        decision["status"]
        == "verified",
        "strong evidence verified",
    )

    review = build_item()

    review["metadata"][
        "needs_review"
    ] = True

    decision = (
        get_verification_decision(
            review
        )
    )

    check(
        decision["status"]
        != "verified",
        "review flag prevents verification",
    )

    weak = {
        "title":
            "ร้านพบจากเว็บ",
        "location": {
            "province":
                "ปราจีนบุรี",
            "latitude":
                None,
            "longitude":
                None,
        },
        "metadata": {
            "display_tier":
                "named_candidate",
            "needs_review":
                True,
            "evidence_reason":
                "web_listing",
        },
        "source_url":
            "https://example.com/place",
    }

    result = (
        calculate_confidence(
            weak
        )
    )

    check(
        result["level"]
        == "low",
        "weak evidence remains low confidence",
    )

    market = build_item()

    market["metadata"][
        "verification_source"
    ] = "verified_business_listing"

    market["metadata"][
        "coordinate_precision"
    ] = "market"

    result = (
        calculate_confidence(
            market
        )
    )

    check(
        result["score"] >= 50,
        "market-level verified location accepted",
    )

    print()
    print("=" * 60)
    print(
        "PLACE DISCOVERY VERIFICATION CORE"
    )
    print(
        "FINAL RESULT: PASS"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
