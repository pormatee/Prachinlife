import json
from pathlib import Path


MANIFEST = Path(
    "data/config/place_discovery_engine_v1_manifest.json"
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def main():
    data = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    check(
        data["status"] == "frozen_v1",
        "freeze status preserved",
    )

    rules = data[
        "architecture_rules"
    ]

    required_true = [
        "single_discovery_engine",
        "category_driven",
        "province_forks_forbidden",
        "provider_zero_results_do_not_mean_no_places",
        "incomplete_coverage_must_be_explicit",
        "unverified_candidates_must_not_enter_primary",
        "duplicate_check_required_before_merge",
        "coordinates_required_for_primary_near_me",
        "ai_may_not_bypass_merge_policy",
        "ai_may_not_disable_regression_tests",
    ]

    for key in required_true:
        check(
            rules.get(key) is True,
            key,
        )

    check(
        data["reference_category"]
        == "vegetarian",
        "vegetarian reference category preserved",
    )

    check(
        "eat" in data["next_categories"],
        "eat category authorized next",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY ENGINE V1 MANIFEST")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
