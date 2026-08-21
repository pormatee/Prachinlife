from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.place_discovery_identity import (
    normalize_text,
    haversine_km,
)


INPUT = Path("service_index.json")

OUTPUT = Path(
    "data/candidates/"
    "service_index_qualified_v1.json"
)

REPORT = Path(
    "data/candidates/"
    "service_qualification_report_v1.json"
)

DUPLICATE_DISTANCE_KM = 0.15

ALLOWED_CATEGORIES = {
    "pharmacy",
    "clinic",
    "fuel",
    "car_repair",
    "laundry",
}


def coordinates(row):
    location = row.get("location") or {}

    lat = location.get("latitude")
    lon = location.get("longitude")

    if (
        not isinstance(lat, (int, float))
        or
        not isinstance(lon, (int, float))
    ):
        return None

    return float(lat), float(lon)


def same_service_place(a, b):
    if (
        a.get("id")
        and
        a.get("id") == b.get("id")
    ):
        return True, 0.0, "same_id"

    if a.get("category") != b.get("category"):
        return False, None, "different_category"

    title_a = normalize_text(
        a.get("title")
    )

    title_b = normalize_text(
        b.get("title")
    )

    if (
        not title_a
        or
        title_a != title_b
    ):
        return False, None, "different_title"

    coord_a = coordinates(a)
    coord_b = coordinates(b)

    if (
        coord_a is None
        or
        coord_b is None
    ):
        return (
            False,
            None,
            "same_title_no_coordinate_review"
        )

    distance = haversine_km(
        coord_a[0],
        coord_a[1],
        coord_b[0],
        coord_b[1],
    )

    duplicate = (
        distance
        <= DUPLICATE_DISTANCE_KM
    )

    return (
        duplicate,
        distance,
        (
            "same_title_nearby"
            if duplicate
            else "same_title_different_branch"
        ),
    )


def main():
    rows = json.loads(
        INPUT.read_text(
            encoding="utf-8"
        )
    )

    kept = []
    duplicates = []

    for row in rows:

        assert (
            row.get("content_type")
            == "service"
        )

        assert (
            row.get("category")
            in ALLOWED_CATEGORIES
        )

        assert row.get("title")
        assert coordinates(row) is not None
        assert row.get("source_url")

        duplicate_of = None
        duplicate_decision = None

        for existing in kept:

            duplicate, distance, reason = (
                same_service_place(
                    row,
                    existing,
                )
            )

            if duplicate:
                duplicate_of = existing
                duplicate_decision = {
                    "reason": reason,
                    "distance_km":
                        distance,
                }
                break

        if duplicate_of:

            duplicates.append({
                "candidate_id":
                    row.get("id"),

                "candidate_title":
                    row.get("title"),

                "duplicate_of_id":
                    duplicate_of.get("id"),

                "duplicate_of_title":
                    duplicate_of.get("title"),

                "decision":
                    duplicate_decision,
            })

            continue

        copy = dict(row)

        metadata = dict(
            copy.get("metadata")
            or {}
        )

        metadata.update({
            "display_tier":
                "primary",

            "show_in_primary_directory":
                True,

            "needs_review":
                False,

            "review_reason":
                None,

            "qualification_policy":
                "service_v1_spatial_identity",
        })

        copy["metadata"] = metadata

        kept.append(copy)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            kept,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    category_counts = Counter(
        row["category"]
        for row in kept
    )

    report = {
        "input_count":
            len(rows),

        "qualified_count":
            len(kept),

        "duplicate_count":
            len(duplicates),

        "duplicate_distance_km":
            DUPLICATE_DISTANCE_KM,

        "category_counts":
            dict(category_counts),

        "duplicates":
            duplicates,
    }

    REPORT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "INPUT      =",
        len(rows)
    )

    print(
        "QUALIFIED  =",
        len(kept)
    )

    print(
        "DUPLICATES =",
        len(duplicates)
    )

    print(
        "CATEGORY   =",
        category_counts
    )

    print()
    print(
        "PASS: Service V1 qualification completed"
    )


if __name__ == "__main__":
    main()
