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

from scripts.place_discovery_location import (
    get_province_config,
    split_bbox,
    point_in_bbox,
    point_in_province_bbox,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def main():
    prachin = get_province_config(
        "ปราจีนบุรี"
    )

    check(
        prachin["bbox"]
        == [13.55, 101.1, 14.45, 102.2],
        "Prachinburi bbox preserved",
    )

    grids = split_bbox(
        prachin["bbox"],
        rows=2,
        cols=2,
    )

    check(
        len(grids) == 4,
        "2x2 grid produces 4 cells",
    )

    check(
        grids[0]
        == [13.55, 101.1, 14.0, 101.65],
        "grid 1 boundary preserved",
    )

    check(
        grids[3]
        == [14.0, 101.65, 14.45, 102.2],
        "grid 4 boundary preserved",
    )

    check(
        point_in_province_bbox(
            14.05236,
            101.36833,
            "ปราจีนบุรี",
        ),
        "known Prachinburi point accepted",
    )

    check(
        not point_in_province_bbox(
            13.7563,
            100.5018,
            "ปราจีนบุรี",
        ),
        "Bangkok point rejected",
    )

    check(
        point_in_bbox(
            13.55,
            101.1,
            prachin["bbox"],
        ),
        "bbox boundary inclusive",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY LOCATION CORE")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
