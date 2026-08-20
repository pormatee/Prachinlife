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

from scripts.place_discovery_identity import (
    compare_identity,
    find_duplicates,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def build_item(
    *,
    item_id,
    title,
    province="ปราจีนบุรี",
    lat=14.05,
    lon=101.37,
):
    return {
        "id": item_id,
        "title": title,
        "location": {
            "province":
                province,
            "latitude":
                lat,
            "longitude":
                lon,
        },
    }


def main():
    a = build_item(
        item_id="same-1",
        title="อาหารเจ ซั่นสี่",
    )

    b = build_item(
        item_id="same-1",
        title="ชื่ออื่น",
    )

    result = compare_identity(
        a,
        b,
    )

    check(
        result["duplicate"],
        "same ID detected",
    )

    a = build_item(
        item_id="a",
        title="อาหารเจ ซั่นสี่",
    )

    b = build_item(
        item_id="b",
        title="อาหารเจ ซั่นสี่",
    )

    result = compare_identity(
        a,
        b,
    )

    check(
        result["duplicate"],
        "same title/province detected",
    )

    a = build_item(
        item_id="a",
        title="อาหารเจ ซั่นสี่",
    )

    b = build_item(
        item_id="b",
        title="อาหารเจ ซั่นสี่",
        province="ฉะเชิงเทรา",
    )

    result = compare_identity(
        a,
        b,
    )

    check(
        not result["duplicate"],
        "different province preserved",
    )

    a = build_item(
        item_id="a",
        title="ร้านอาหารเจสุขใจ",
    )

    b = build_item(
        item_id="b",
        title="ร้านอาหารเจสุขใจ",
        lat=14.051,
        lon=101.371,
    )

    matches = find_duplicates(
        a,
        [b],
    )

    check(
        len(matches) == 1,
        "duplicate search finds match",
    )

    a = build_item(
        item_id="a",
        title="ร้านอาหารเจสุขใจ",
    )

    b = build_item(
        item_id="b",
        title="Green Vegetarian Cafe",
    )

    result = compare_identity(
        a,
        b,
    )

    check(
        not result["duplicate"],
        "different title preserved",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY IDENTITY CORE")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
