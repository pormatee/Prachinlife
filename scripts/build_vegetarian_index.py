from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "vegetarian_places.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "vegetarian_index.json"
)


# ============================================================
# VERSION
# ============================================================

BUILDER_NAME = (
    "PrachinLife Vegetarian Index Builder"
)

BUILDER_VERSION = "1.0"


# ============================================================
# LOAD / SAVE
# ============================================================

def load_json(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            "Input JSON must be an array"
        )

    return [
        item
        for item in data
        if isinstance(
            item,
            dict,
        )
    ]


def save_json(
    path: Path,
    records: list[dict[str, Any]],
) -> None:

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# VALIDATION HELPERS
# ============================================================

def has_coordinates(
    item: dict[str, Any],
) -> bool:

    location = (
        item.get(
            "location"
        )
    )

    if not isinstance(
        location,
        dict,
    ):
        return False

    latitude = (
        location.get(
            "latitude"
        )
    )

    longitude = (
        location.get(
            "longitude"
        )
    )

    return (
        latitude is not None
        and
        longitude is not None
    )


def has_name(
    item: dict[str, Any],
) -> bool:

    name = (
        item.get(
            "name"
        )
    )

    return bool(
        isinstance(
            name,
            str,
        )
        and
        name.strip()
    )


def has_positive_dietary_status(
    item: dict[str, Any],
) -> bool:

    return (
        item.get(
            "vegetarian_status"
        )
        ==
        "confirmed"

        or

        item.get(
            "vegan_status"
        )
        ==
        "confirmed"

        or

        item.get(
            "jay_status"
        )
        ==
        "confirmed"
    )


def should_publish(
    item: dict[str, Any],
) -> bool:

    return (
        item.get(
            "displayable"
        )
        is True

        and

        has_name(
            item
        )

        and

        has_coordinates(
            item
        )

        and

        has_positive_dietary_status(
            item
        )
    )


# ============================================================
# NORMALIZE INDEX RECORD
# ============================================================

def build_index_record(
    item: dict[str, Any],
) -> dict[str, Any]:

    location = (
        item.get(
            "location"
        )
        or
        {}
    )

    dietary = (
        item.get(
            "dietary"
        )
        or
        {}
    )

    source = (
        item.get(
            "source"
        )
        or
        {}
    )

    contact = (
        item.get(
            "contact"
        )
        or
        {}
    )

    return {
        "schema_version":
            "1.0",

        "id":
            item.get(
                "id"
            ),

        "content_type":
            "vegetarian_place",

        "title":
            item.get(
                "name"
            ),

        "category":
            item.get(
                "category"
            ),

        "cuisine":
            item.get(
                "cuisine"
            )
            or [],

        "dietary": {
            "vegetarian_status":
                item.get(
                    "vegetarian_status"
                )
                or
                "unknown",

            "vegan_status":
                item.get(
                    "vegan_status"
                )
                or
                "unknown",

            "jay_status":
                item.get(
                    "jay_status"
                )
                or
                "unknown",
        },

        "location": {
            "country":
                location.get(
                    "country"
                )
                or
                "TH",

            "province":
                location.get(
                    "province"
                ),

            "province_iso":
                location.get(
                    "province_iso"
                ),

            "district":
                location.get(
                    "district"
                ),

            "subdistrict":
                location.get(
                    "subdistrict"
                ),

            "street":
                location.get(
                    "street"
                ),

            "postcode":
                location.get(
                    "postcode"
                ),

            "latitude":
                location.get(
                    "latitude"
                ),

            "longitude":
                location.get(
                    "longitude"
                ),
        },

        "opening_hours":
            item.get(
                "opening_hours"
            ),

        "contact": {
            "phone":
                contact.get(
                    "phone"
                ),

            "website":
                contact.get(
                    "website"
                ),

            "facebook":
                contact.get(
                    "facebook"
                ),
        },

        "source": {
            "name":
                source.get(
                    "name"
                ),

            "type":
                source.get(
                    "type"
                ),

            "url":
                source.get(
                    "url"
                ),

            "verified":
                source.get(
                    "verified"
                )
                is True,
        },

        "owner_verified":
            item.get(
                "owner_verified"
            )
            is True,

        "sponsored":
            item.get(
                "sponsored"
            )
            is True,

        "collected_at":
            item.get(
                "collected_at"
            ),
    }


# ============================================================
# VALIDATE OUTPUT
# ============================================================

def validate_index(
    records: list[dict[str, Any]],
) -> None:

    seen_ids: set[str] = set()

    for index, item in enumerate(
        records,
        start=1,
    ):

        item_id = (
            item.get(
                "id"
            )
        )

        if not item_id:
            raise ValueError(
                f"record {index}: missing id"
            )

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: duplicate id {item_id}"
            )

        seen_ids.add(
            str(
                item_id
            )
        )

        if (
            item.get(
                "content_type"
            )
            !=
            "vegetarian_place"
        ):
            raise ValueError(
                f"{item_id}: invalid content_type"
            )

        title = (
            item.get(
                "title"
            )
        )

        if not (
            isinstance(
                title,
                str,
            )
            and
            title.strip()
        ):
            raise ValueError(
                f"{item_id}: missing title"
            )

        location = (
            item.get(
                "location"
            )
        )

        if not isinstance(
            location,
            dict,
        ):
            raise ValueError(
                f"{item_id}: missing location"
            )

        if (
            location.get(
                "latitude"
            )
            is None
            or
            location.get(
                "longitude"
            )
            is None
        ):
            raise ValueError(
                f"{item_id}: missing coordinates"
            )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    raw_records: list[dict[str, Any]],
    index_records: list[dict[str, Any]],
) -> None:

    province_counts: dict[
        str,
        int
    ] = {}

    vegetarian_count = 0
    vegan_count = 0
    jay_count = 0

    for item in index_records:

        location = (
            item.get(
                "location"
            )
            or
            {}
        )

        province = (
            location.get(
                "province"
            )
            or
            "unknown"
        )

        province_counts[
            province
        ] = (
            province_counts.get(
                province,
                0,
            )
            + 1
        )

        dietary = (
            item.get(
                "dietary"
            )
            or
            {}
        )

        if (
            dietary.get(
                "vegetarian_status"
            )
            ==
            "confirmed"
        ):
            vegetarian_count += 1

        if (
            dietary.get(
                "vegan_status"
            )
            ==
            "confirmed"
        ):
            vegan_count += 1

        if (
            dietary.get(
                "jay_status"
            )
            ==
            "confirmed"
        ):
            jay_count += 1


    print()

    print("=" * 60)

    print(
        "VEGETARIAN INDEX SUMMARY"
    )

    print("=" * 60)

    print(
        "Raw records =",
        len(raw_records),
    )

    print(
        "Published records =",
        len(index_records),
    )

    print(
        "Filtered out =",
        (
            len(raw_records)
            -
            len(index_records)
        ),
    )

    print(
        "Vegetarian confirmed =",
        vegetarian_count,
    )

    print(
        "Vegan confirmed =",
        vegan_count,
    )

    print(
        "Jay confirmed =",
        jay_count,
    )

    print(
        "Province counts =",
        province_counts,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 60)

    print(
        BUILDER_NAME
    )

    print(
        "Version",
        BUILDER_VERSION,
    )

    print("=" * 60)


    raw_records = (
        load_json(
            RAW_FILE
        )
    )


    index_records: list[
        dict[str, Any]
    ] = []


    for item in raw_records:

        if not (
            should_publish(
                item
            )
        ):
            continue

        index_record = (
            build_index_record(
                item
            )
        )

        index_records.append(
            index_record
        )


    index_records.sort(
        key=lambda item: (
            (
                item.get(
                    "location",
                    {}
                )
                .get(
                    "province"
                )
                or
                ""
            ),
            (
                item.get(
                    "title"
                )
                or
                ""
            ),
            (
                item.get(
                    "id"
                )
                or
                ""
            ),
        )
    )


    validate_index(
        index_records
    )


    save_json(
        OUTPUT_FILE,
        index_records,
    )


    print_summary(
        raw_records,
        index_records,
    )


    print()

    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print()

    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":

    main()
