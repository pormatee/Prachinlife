from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
)

OUTPUT_FILE = (
    RAW_DIR
    / "restaurants_osm.json"
)


OVERPASS_URL = (
    "https://overpass-api.de/api/interpreter"
)


USER_AGENT = (
    "PrachinLife/1.0 "
    "(Prachinburi local information project)"
)


REQUEST_TIMEOUT = 120

MAX_RETRIES = 3


AMENITIES = [
    "restaurant",
    "cafe",
    "fast_food",
    "food_court",
    "ice_cream",
]


def build_query() -> str:

    amenity_regex = "|".join(
        AMENITIES
    )

    return f"""
[out:json][timeout:90];

area
  ["boundary"="administrative"]
  ["name"="ปราจีนบุรี"]
  ->.searchArea;

(
  node
    ["amenity"~"^({amenity_regex})$"]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    (area.searchArea);
);

out center tags;
"""


def fetch_overpass(
    query: str,
) -> dict[str, Any]:

    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            print(
                f"Overpass request "
                f"attempt {attempt}/"
                f"{MAX_RETRIES}"
            )

            response = requests.post(
                OVERPASS_URL,
                data={
                    "data": query,
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(
                data,
                dict,
            ):
                raise ValueError(
                    "Overpass response "
                    "must be a JSON object"
                )

            return data

        except (
            requests.RequestException,
            ValueError,
        ) as error:

            last_error = error

            print(
                "Overpass request failed:",
                error,
            )

            if attempt < MAX_RETRIES:

                wait_seconds = (
                    attempt * 5
                )

                print(
                    "Retrying in",
                    wait_seconds,
                    "seconds..."
                )

                time.sleep(
                    wait_seconds
                )

    raise RuntimeError(
        "Overpass request failed "
        "after retries"
    ) from last_error


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


def get_coordinates(
    element: dict[str, Any],
) -> tuple[
    float | None,
    float | None,
]:

    lat = element.get(
        "lat"
    )

    lon = element.get(
        "lon"
    )

    if (
        lat is not None
        and lon is not None
    ):

        return (
            float(lat),
            float(lon),
        )

    center = element.get(
        "center"
    )

    if isinstance(
        center,
        dict,
    ):

        center_lat = center.get(
            "lat"
        )

        center_lon = center.get(
            "lon"
        )

        if (
            center_lat is not None
            and center_lon is not None
        ):

            return (
                float(
                    center_lat
                ),
                float(
                    center_lon
                ),
            )

    return (
        None,
        None,
    )


def build_address(
    tags: dict[str, Any],
) -> dict[str, Any]:

    return {
        "house_number":
            clean_text(
                tags.get(
                    "addr:housenumber"
                )
            ),

        "street":
            clean_text(
                tags.get(
                    "addr:street"
                )
            ),

        "subdistrict":
            (
                clean_text(
                    tags.get(
                        "addr:subdistrict"
                    )
                )
                or
                clean_text(
                    tags.get(
                        "addr:suburb"
                    )
                )
            ),

        "district":
            (
                clean_text(
                    tags.get(
                        "addr:district"
                    )
                )
                or
                clean_text(
                    tags.get(
                        "addr:city"
                    )
                )
            ),

        "province":
            (
                clean_text(
                    tags.get(
                        "addr:province"
                    )
                )
                or
                "ปราจีนบุรี"
            ),

        "postcode":
            clean_text(
                tags.get(
                    "addr:postcode"
                )
            ),
    }


def normalize_element(
    element: dict[str, Any],
    collected_at: str,
) -> dict[str, Any] | None:

    element_type = clean_text(
        element.get(
            "type"
        )
    )

    element_id = element.get(
        "id"
    )

    tags = element.get(
        "tags"
    )

    if (
        not element_type
        or element_id is None
        or not isinstance(
            tags,
            dict,
        )
    ):
        return None

    amenity = clean_text(
        tags.get(
            "amenity"
        )
    )

    if amenity not in AMENITIES:
        return None

    name = (
        clean_text(
            tags.get(
                "name"
            )
        )
        or
        clean_text(
            tags.get(
                "name:th"
            )
        )
        or
        clean_text(
            tags.get(
                "name:en"
            )
        )
    )

    latitude, longitude = (
        get_coordinates(
            element
        )
    )

    return {
        "id":
            f"osm-{element_type}-"
            f"{element_id}",

        "osm_type":
            element_type,

        "osm_id":
            element_id,

        "name":
            name,

        "name_th":
            clean_text(
                tags.get(
                    "name:th"
                )
            ),

        "name_en":
            clean_text(
                tags.get(
                    "name:en"
                )
            ),

        "amenity":
            amenity,

        "cuisine":
            clean_text(
                tags.get(
                    "cuisine"
                )
            ),

        "opening_hours":
            clean_text(
                tags.get(
                    "opening_hours"
                )
            ),

        "phone":
            (
                clean_text(
                    tags.get(
                        "contact:phone"
                    )
                )
                or
                clean_text(
                    tags.get(
                        "phone"
                    )
                )
            ),

        "website":
            (
                clean_text(
                    tags.get(
                        "contact:website"
                    )
                )
                or
                clean_text(
                    tags.get(
                        "website"
                    )
                )
            ),

        "facebook":
            clean_text(
                tags.get(
                    "contact:facebook"
                )
            ),

        "wheelchair":
            clean_text(
                tags.get(
                    "wheelchair"
                )
            ),

        "takeaway":
            clean_text(
                tags.get(
                    "takeaway"
                )
            ),

        "delivery":
            clean_text(
                tags.get(
                    "delivery"
                )
            ),

        "outdoor_seating":
            clean_text(
                tags.get(
                    "outdoor_seating"
                )
            ),

        "internet_access":
            clean_text(
                tags.get(
                    "internet_access"
                )
            ),

        "latitude":
            latitude,

        "longitude":
            longitude,

        "address":
            build_address(
                tags
            ),

        "source": {
            "name":
                "OpenStreetMap",

            "type":
                "open_data",

            "osm_type":
                element_type,

            "osm_id":
                element_id,
        },

        "collected_at":
            collected_at,

        "raw_tags":
            tags,
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
                f"record {index}: "
                "missing id"
            )

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: "
                f"duplicate id "
                f"{item_id}"
            )

        seen_ids.add(
            item_id
        )

        if (
            item.get(
                "amenity"
            )
            not in AMENITIES
        ):
            raise ValueError(
                f"{item_id}: "
                "invalid amenity"
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
        "OpenStreetMap Eat Collector V1"
    )

    print("=" * 60)

    query = build_query()

    data = fetch_overpass(
        query
    )

    elements = data.get(
        "elements",
        []
    )

    if not isinstance(
        elements,
        list,
    ):
        raise ValueError(
            "Overpass elements "
            "must be a list"
        )

    collected_at = (
        datetime
        .astimezone(
            datetime.now()
        )
        .isoformat()
    )

    records: list[
        dict[str, Any]
    ] = []

    for element in elements:

        if not isinstance(
            element,
            dict,
        ):
            continue

        normalized = (
            normalize_element(
                element,
                collected_at,
            )
        )

        if normalized:

            records.append(
                normalized
            )

    validate_records(
        records
    )

    records.sort(
        key=lambda item: (
            item.get(
                "name"
            )
            or "",
            item.get(
                "id"
            )
            or "",
        )
    )

    save_json(
        OUTPUT_FILE,
        records,
    )

    amenity_counts: dict[
        str,
        int,
    ] = {}

    named_count = 0

    coordinate_count = 0

    for item in records:

        amenity = (
            item.get(
                "amenity"
            )
            or "unknown"
        )

        amenity_counts[
            amenity
        ] = (
            amenity_counts.get(
                amenity,
                0,
            )
            + 1
        )

        if item.get(
            "name"
        ):
            named_count += 1

        if (
            item.get(
                "latitude"
            )
            is not None
            and
            item.get(
                "longitude"
            )
            is not None
        ):
            coordinate_count += 1

    print()

    print(
        "OSM elements =",
        len(elements),
    )

    print(
        "Collected records =",
        len(records),
    )

    print(
        "Named records =",
        named_count,
    )

    print(
        "Records with coordinates =",
        coordinate_count,
    )

    print(
        "Amenity counts =",
        amenity_counts,
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
