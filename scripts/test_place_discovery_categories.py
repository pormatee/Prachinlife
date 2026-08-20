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

from scripts.place_discovery_categories import (
    get_category_config,
    get_osm_amenity_regex,
    get_query_keyword_regex,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def main():
    veg = get_category_config(
        "vegetarian"
    )

    check(
        veg["content_type"] == "vegetarian",
        "vegetarian content type preserved",
    )

    amenity_regex = get_osm_amenity_regex(
        "vegetarian"
    )

    check(
        "restaurant" in amenity_regex,
        "restaurant amenity preserved",
    )

    check(
        "cafe" in amenity_regex,
        "cafe amenity preserved",
    )

    all_keywords = get_query_keyword_regex(
        "vegetarian"
    )

    thai_keywords = get_query_keyword_regex(
        "vegetarian",
        thai_only=True,
    )

    check(
        "อาหารเจ" in all_keywords,
        "jay keyword preserved",
    )

    check(
        "vegetarian" in all_keywords,
        "vegetarian keyword preserved",
    )

    check(
        "vegan" in all_keywords,
        "vegan keyword preserved",
    )

    check(
        "อาหารเจ" in thai_keywords,
        "Thai jay query preserved",
    )

    check(
        "vegetarian" not in thai_keywords,
        "English keyword excluded from Thai-only query",
    )

    keywords = veg["keywords"]

    check(
        keywords["jay_shop_regex"]
        == r"ร้าน\s*เจ(?![่้๊๋า-ูเ-์])",
        "jay false-positive regex preserved",
    )

    classification = veg[
        "classification"
    ]

    check(
        "only"
        in classification[
            "dedicated_values"
        ],
        "dedicated value preserved",
    )

    check(
        "yes"
        in classification[
            "option_values"
        ],
        "option value preserved",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY CATEGORY CORE")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
