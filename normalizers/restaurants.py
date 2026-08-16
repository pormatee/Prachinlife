from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "restaurants_osm.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "normalized"
    / "restaurants.json"
)


ALLOWED_AMENITIES = {
    "restaurant",
    "cafe",
    "fast_food",
    "food_court",
    "ice_cream",
}


def load_json_list(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"Missing source file: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            f"{path} must contain a JSON list"
        )

    return [
        item
        for item in data
        if isinstance(
            item,
            dict,
        )
    ]


def clean_text(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text


def split_cuisine(
    value: Any,
) -> list[str]:

    text = clean_text(
        value
    )

    if not text:
        return []

    values = []

    for part in (
        text
        .replace(
            ",",
            ";"
        )
        .split(";")
    ):

        cleaned = (
            part
            .strip()
            .lower()
        )

        if (
            cleaned
            and cleaned not in values
        ):
            values.append(
                cleaned
            )

    return values


def get_category_label(
    amenity: str,
) -> str:

    mapping = {
        "restaurant":
            "ร้านอาหาร",

        "cafe":
            "คาเฟ่",

        "fast_food":
            "อาหารจานด่วน",

        "food_court":
            "ศูนย์อาหาร",

        "ice_cream":
            "ไอศกรีม",
    }

    return mapping.get(
        amenity,
        "อาหารและเครื่องดื่ม",
    )


def build_osm_url(
    osm_type: str,
    osm_id: Any,
) -> str | None:

    if (
        not osm_type
        or osm_id is None
    ):
        return None

    if osm_type not in {
        "node",
        "way",
        "relation",
    }:
        return None

    return (
        "https://www.openstreetmap.org/"
        f"{osm_type}/"
        f"{osm_id}"
    )


def normalize_record(
    item: dict[str, Any],
) -> dict[str, Any] | None:

    item_id = clean_text(
        item.get(
            "id"
        )
    )

    name = (
        clean_text(
            item.get(
                "name"
            )
        )
        or
        clean_text(
            item.get(
                "name_th"
            )
        )
        or
        clean_text(
            item.get(
                "name_en"
            )
        )
    )

    amenity = clean_text(
        item.get(
            "amenity"
        )
    )

    if not item_id:
        return None

    if not name:
        return None

    if (
        amenity
        not in ALLOWED_AMENITIES
    ):
        return None

    address = item.get(
        "address"
    )

    if not isinstance(
        address,
        dict,
    ):
        address = {}

    osm_type = clean_text(
        item.get(
            "osm_type"
        )
    )

    osm_id = item.get(
        "osm_id"
    )

    latitude = item.get(
        "latitude"
    )

    longitude = item.get(
        "longitude"
    )

    return {
        "schema_version":
            "1.0",

        "id":
            item_id,

        "content_type":
            "eat",

        "name":
            name,

        "name_th":
            clean_text(
                item.get(
                    "name_th"
                )
            ),

        "name_en":
            clean_text(
                item.get(
                    "name_en"
                )
            ),

        "category":
            amenity,

        "category_label":
            get_category_label(
                amenity
            ),

        "cuisine":
            split_cuisine(
                item.get(
                    "cuisine"
                )
            ),

        "opening_hours":
            clean_text(
                item.get(
                    "opening_hours"
                )
            ),

        "location": {
            "country":
                "TH",

            "province":
                "ปราจีนบุรี",

            "district":
                clean_text(
                    address.get(
                        "district"
                    )
                ),

            "subdistrict":
                clean_text(
                    address.get(
                        "subdistrict"
                    )
                ),

            "street":
                clean_text(
                    address.get(
                        "street"
                    )
                ),

            "house_number":
                clean_text(
                    address.get(
                        "house_number"
                    )
                ),

            "postcode":
                clean_text(
                    address.get(
                        "postcode"
                    )
                ),

            "latitude":
                latitude,

            "longitude":
                longitude,
        },

        "contact": {
            "phone":
                clean_text(
                    item.get(
                        "phone"
                    )
                ),

            "website":
                clean_text(
                    item.get(
                        "website"
                    )
                ),

            "facebook":
                clean_text(
                    item.get(
                        "facebook"
                    )
                ),
        },

        "features": {
            "takeaway":
                clean_text(
                    item.get(
                        "takeaway"
                    )
                ),

            "delivery":
                clean_text(
                    item.get(
                        "delivery"
                    )
                ),

            "outdoor_seating":
                clean_text(
                    item.get(
                        "outdoor_seating"
                    )
                ),

            "wheelchair":
                clean_text(
                    item.get(
                        "wheelchair"
                    )
                ),

            "internet_access":
                clean_text(
                    item.get(
                        "internet_access"
                    )
                ),
        },

        "source": {
            "name":
                "OpenStreetMap",

            "type":
                "open_data",

            "url":
                build_osm_url(
                    osm_type,
                    osm_id,
                ),

            "verified":
                True,
        },

        "collected_at":
            item.get(
                "collected_at"
            ),
    }


def validate_records(
    records: list[dict[str, Any]],
) -> None:

    seen_ids: set[str] = set()

    for index, item in enumerate(
        records,
        start=1,
    ):

        item_id = item.get(
            "id"
        )

        if not item_id:
            raise ValueError(
                f"record {index}: missing id"
            )

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: "
                f"duplicate id {item_id}"
            )

        seen_ids.add(
            item_id
        )

        if not item.get(
            "name"
        ):
            raise ValueError(
                f"{item_id}: missing name"
            )

        if (
            item.get(
                "content_type"
            )
            != "eat"
        ):
            raise ValueError(
                f"{item_id}: "
                "content_type must be eat"
            )

        source = item.get(
            "source"
        )

        if not isinstance(
            source,
            dict,
        ):
            raise ValueError(
                f"{item_id}: invalid source"
            )

        if source.get(
            "verified"
        ) is not True:
            raise ValueError(
                f"{item_id}: "
                "source must be verified"
            )


def save_json(
    path: Path,
    records: list[dict[str, Any]],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def main() -> None:

    print("=" * 60)

    print(
        "PrachinLife - "
        "Eat Normalizer V1"
    )

    print("=" * 60)

    raw_records = load_json_list(
        RAW_FILE
    )

    normalized = []

    skipped_without_name = 0

    for item in raw_records:

        result = normalize_record(
            item
        )

        if result is None:

            if not (
                item.get(
                    "name"
                )
                or
                item.get(
                    "name_th"
                )
                or
                item.get(
                    "name_en"
                )
            ):
                skipped_without_name += 1

            continue

        normalized.append(
            result
        )

    normalized.sort(
        key=lambda item: (
            str(
                item.get(
                    "category"
                )
                or ""
            ),
            str(
                item.get(
                    "name"
                )
                or ""
            ).lower(),
        )
    )

    validate_records(
        normalized
    )

    save_json(
        OUTPUT_FILE,
        normalized,
    )

    category_counts: dict[
        str,
        int,
    ] = {}

    for item in normalized:

        category = (
            item.get(
                "category"
            )
            or "unknown"
        )

        category_counts[
            category
        ] = (
            category_counts.get(
                category,
                0,
            )
            + 1
        )

    print(
        "Raw records =",
        len(raw_records),
    )

    print(
        "Normalized records =",
        len(normalized),
    )

    print(
        "Skipped without name =",
        skipped_without_name,
    )

    print(
        "Category counts =",
        category_counts,
    )

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
