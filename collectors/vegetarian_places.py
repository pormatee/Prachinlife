from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
)

OUTPUT_FILE = (
    RAW_DIR
    / "vegetarian_places.json"
)


# ============================================================
# VERSION
# ============================================================

COLLECTOR_NAME = (
    "PrachinLife Vegetarian Places Collector"
)

COLLECTOR_VERSION = "1.1"


# ============================================================
# OVERPASS CONFIG
# ============================================================

OVERPASS_URL = (
    "https://overpass-api.de/api/interpreter"
)

USER_AGENT = (
    "PrachinLife/1.1 "
    "(Vegetarian and vegan place discovery)"
)

REQUEST_TIMEOUT = 120
MAX_RETRIES = 3


# ============================================================
# PROVINCE CONFIG
# ============================================================

PROVINCES = {
    "ปราจีนบุรี": {
        "iso3166_2": "TH-25",
        "name_en": "Prachin Buri",
    },
}


ACTIVE_PROVINCES = [
    "ปราจีนบุรี",
]


# ============================================================
# PLACE TYPES
# ============================================================

AMENITIES = [
    "restaurant",
    "cafe",
    "fast_food",
    "food_court",
    "ice_cream",
]


# ============================================================
# HELPERS
# ============================================================

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


def normalize_diet_value(
    value: Any,
) -> str | None:

    text = clean_text(
        value
    )

    if text is None:
        return None

    return text.lower()


def split_semicolon_values(
    value: Any,
) -> list[str]:

    text = clean_text(
        value
    )

    if text is None:
        return []

    values: list[str] = []

    for part in text.split(";"):

        cleaned = (
            part
            .strip()
            .lower()
        )

        if cleaned:
            values.append(
                cleaned
            )

    return values


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
                float(center_lat),
                float(center_lon),
            )

    return (
        None,
        None,
    )


def build_address(
    tags: dict[str, Any],
    province_name: str,
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
                province_name
            ),

        "postcode":
            clean_text(
                tags.get(
                    "addr:postcode"
                )
            ),
    }


# ============================================================
# STATUS HELPERS
# ============================================================

def status_from_diet_value(
    value: str | None,
    cuisine_positive: bool,
) -> str:

    if value in {
        "yes",
        "only",
        "limited",
    }:
        return "confirmed"

    if value == "no":
        return "not_available"

    if cuisine_positive:
        return "confirmed"

    return "unknown"


def is_displayable(
    name: str | None,
    latitude: float | None,
    longitude: float | None,
) -> bool:

    return bool(
        name
        and
        latitude is not None
        and
        longitude is not None
    )


# ============================================================
# EVIDENCE DETECTION
# ============================================================

def detect_dietary_evidence(
    tags: dict[str, Any],
) -> dict[str, Any]:

    vegetarian_tag = (
        normalize_diet_value(
            tags.get(
                "diet:vegetarian"
            )
        )
    )

    vegan_tag = (
        normalize_diet_value(
            tags.get(
                "diet:vegan"
            )
        )
    )

    cuisine_values = (
        split_semicolon_values(
            tags.get(
                "cuisine"
            )
        )
    )

    cuisine_vegetarian = (
        "vegetarian"
        in cuisine_values
    )

    cuisine_vegan = (
        "vegan"
        in cuisine_values
    )


    vegetarian_evidence: list[
        dict[str, Any]
    ] = []

    vegan_evidence: list[
        dict[str, Any]
    ] = []


    if vegetarian_tag is not None:

        vegetarian_evidence.append({
            "field":
                "diet:vegetarian",

            "value":
                vegetarian_tag,
        })


    if vegan_tag is not None:

        vegan_evidence.append({
            "field":
                "diet:vegan",

            "value":
                vegan_tag,
        })


    if cuisine_vegetarian:

        vegetarian_evidence.append({
            "field":
                "cuisine",

            "value":
                "vegetarian",
        })


    if cuisine_vegan:

        vegan_evidence.append({
            "field":
                "cuisine",

            "value":
                "vegan",
        })


    vegetarian_status = (
        status_from_diet_value(
            vegetarian_tag,
            cuisine_vegetarian,
        )
    )


    vegan_status = (
        status_from_diet_value(
            vegan_tag,
            cuisine_vegan,
        )
    )


    return {
        "vegetarian": {
            "value":
                vegetarian_tag,

            "status":
                vegetarian_status,

            "positive":
                vegetarian_status
                == "confirmed",

            "evidence":
                vegetarian_evidence,
        },

        "vegan": {
            "value":
                vegan_tag,

            "status":
                vegan_status,

            "positive":
                vegan_status
                == "confirmed",

            "evidence":
                vegan_evidence,
        },

        "jay": {
            "value":
                None,

            "status":
                "unknown",

            "positive":
                False,

            "evidence":
                [],
        },
    }


def has_relevant_dietary_evidence(
    evidence: dict[str, Any],
) -> bool:

    vegetarian = (
        evidence.get(
            "vegetarian",
            {}
        )
    )

    vegan = (
        evidence.get(
            "vegan",
            {}
        )
    )

    return bool(
        vegetarian.get(
            "evidence"
        )
        or
        vegan.get(
            "evidence"
        )
    )


# ============================================================
# QUERY
# ============================================================

def build_query(
    iso3166_2: str,
) -> str:

    amenity_regex = (
        "|".join(
            AMENITIES
        )
    )

    return f"""
[out:json][timeout:90];

area
  ["boundary"="administrative"]
  ["ISO3166-2"="{iso3166_2}"]
  ->.searchArea;

(
  node
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegetarian"]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegetarian"]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegetarian"]
    (area.searchArea);


  node
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegan"]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegan"]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegan"]
    (area.searchArea);


  node
    ["amenity"~"^({amenity_regex})$"]
    ["cuisine"~"(^|;)(vegetarian|vegan)(;|$)",i]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    ["cuisine"~"(^|;)(vegetarian|vegan)(;|$)",i]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    ["cuisine"~"(^|;)(vegetarian|vegan)(;|$)",i]
    (area.searchArea);
);

out center tags;
"""


def build_fallback_query(
    iso3166_2: str,
) -> str:

    amenity_regex = (
        "|".join(
            AMENITIES
        )
    )

    return f"""
[out:json][timeout:90];

rel
  ["boundary"="administrative"]
  ["ISO3166-2"="{iso3166_2}"];

map_to_area
  ->.searchArea;

(
  node
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegetarian"]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegetarian"]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegetarian"]
    (area.searchArea);


  node
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegan"]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegan"]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    ["diet:vegan"]
    (area.searchArea);


  node
    ["amenity"~"^({amenity_regex})$"]
    ["cuisine"~"(^|;)(vegetarian|vegan)(;|$)",i]
    (area.searchArea);

  way
    ["amenity"~"^({amenity_regex})$"]
    ["cuisine"~"(^|;)(vegetarian|vegan)(;|$)",i]
    (area.searchArea);

  relation
    ["amenity"~"^({amenity_regex})$"]
    ["cuisine"~"(^|;)(vegetarian|vegan)(;|$)",i]
    (area.searchArea);
);

out center tags;
"""


# ============================================================
# HTTP
# ============================================================

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
                "Overpass request "
                f"attempt {attempt}/"
                f"{MAX_RETRIES}"
            )


            response = requests.post(
                OVERPASS_URL,
                data={
                    "data":
                        query,
                },
                headers=headers,
                timeout=
                    REQUEST_TIMEOUT,
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


            if (
                attempt
                <
                MAX_RETRIES
            ):

                wait_seconds = (
                    attempt
                    * 5
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


# ============================================================
# NORMALIZE
# ============================================================

def normalize_element(
    element: dict[str, Any],
    province_name: str,
    province_iso: str,
    collected_at: str,
) -> dict[str, Any] | None:

    element_type = (
        clean_text(
            element.get(
                "type"
            )
        )
    )


    element_id = (
        element.get(
            "id"
        )
    )


    tags = (
        element.get(
            "tags"
        )
    )


    if (
        not element_type
        or
        element_id is None
        or
        not isinstance(
            tags,
            dict,
        )
    ):

        return None


    amenity = (
        clean_text(
            tags.get(
                "amenity"
            )
        )
    )


    if amenity not in AMENITIES:

        return None


    dietary = (
        detect_dietary_evidence(
            tags
        )
    )


    if not (
        has_relevant_dietary_evidence(
            dietary
        )
    ):

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
        or
        clean_text(
            tags.get(
                "brand"
            )
        )
        or
        clean_text(
            tags.get(
                "operator"
            )
        )
    )


    latitude, longitude = (
        get_coordinates(
            element
        )
    )


    address = (
        build_address(
            tags,
            province_name,
        )
    )


    cuisine = (
        split_semicolon_values(
            tags.get(
                "cuisine"
            )
        )
    )


    source_url = (
        "https://www.openstreetmap.org/"
        f"{element_type}/"
        f"{element_id}"
    )


    displayable = (
        is_displayable(
            name,
            latitude,
            longitude,
        )
    )


    return {
        "schema_version":
            "1.1",

        "id":
            f"osm-{element_type}-"
            f"{element_id}",

        "content_type":
            "vegetarian_place",

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

        "category":
            amenity,

        "cuisine":
            cuisine,

        "dietary":
            dietary,

        "vegetarian_status":
            dietary[
                "vegetarian"
            ][
                "status"
            ],

        "vegan_status":
            dietary[
                "vegan"
            ][
                "status"
            ],

        "jay_status":
            "unknown",

        "displayable":
            displayable,

        "location": {
            "country":
                "TH",

            "province":
                province_name,

            "province_iso":
                province_iso,

            "district":
                address.get(
                    "district"
                ),

            "subdistrict":
                address.get(
                    "subdistrict"
                ),

            "street":
                address.get(
                    "street"
                ),

            "house_number":
                address.get(
                    "house_number"
                ),

            "postcode":
                address.get(
                    "postcode"
                ),

            "latitude":
                latitude,

            "longitude":
                longitude,
        },

        "contact": {
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
        },

        "opening_hours":
            clean_text(
                tags.get(
                    "opening_hours"
                )
            ),

        "source": {
            "name":
                "OpenStreetMap",

            "type":
                "open_data",

            "url":
                source_url,

            "verified":
                True,

            "osm_type":
                element_type,

            "osm_id":
                element_id,
        },

        "owner_verified":
            False,

        "sponsored":
            False,

        "collected_at":
            collected_at,

        "raw_tags":
            tags,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_records(
    records: list[
        dict[str, Any]
    ],
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
                "content_type"
            )
            !=
            "vegetarian_place"
        ):

            raise ValueError(
                f"{item_id}: "
                "invalid content_type"
            )


        dietary = (
            item.get(
                "dietary"
            )
        )


        if not isinstance(
            dietary,
            dict,
        ):

            raise ValueError(
                f"{item_id}: "
                "missing dietary"
            )


        if not (
            has_relevant_dietary_evidence(
                dietary
            )
        ):

            raise ValueError(
                f"{item_id}: "
                "missing dietary evidence"
            )


        if (
            item.get(
                "vegetarian_status"
            )
            not in {
                "confirmed",
                "not_available",
                "unknown",
            }
        ):

            raise ValueError(
                f"{item_id}: "
                "invalid vegetarian_status"
            )


        if (
            item.get(
                "vegan_status"
            )
            not in {
                "confirmed",
                "not_available",
                "unknown",
            }
        ):

            raise ValueError(
                f"{item_id}: "
                "invalid vegan_status"
            )


        if (
            item.get(
                "jay_status"
            )
            !=
            "unknown"
        ):

            raise ValueError(
                f"{item_id}: "
                "Jay inference is prohibited"
            )


        if not isinstance(
            item.get(
                "displayable"
            ),
            bool,
        ):

            raise ValueError(
                f"{item_id}: "
                "displayable must be bool"
            )


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_records(
    records: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:

    unique: dict[
        str,
        dict[str, Any]
    ] = {}


    for item in records:

        item_id = (
            str(
                item.get(
                    "id"
                )
                or
                ""
            )
        )


        if not item_id:

            continue


        unique[
            item_id
        ] = item


    return list(
        unique.values()
    )


# ============================================================
# SAVE
# ============================================================

def save_json(
    path: Path,
    records: list[
        dict[str, Any]
    ],
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


# ============================================================
# COLLECT ONE PROVINCE
# ============================================================

def collect_province(
    province_name: str,
    province_config: dict[
        str,
        str
    ],
    collected_at: str,
) -> list[
    dict[str, Any]
]:

    province_iso = (
        province_config[
            "iso3166_2"
        ]
    )


    print()

    print(
        "-" * 60
    )

    print(
        "Province:",
        province_name,
    )

    print(
        "ISO:",
        province_iso,
    )

    print(
        "-" * 60
    )


    data = fetch_overpass(
        build_query(
            province_iso
        )
    )


    elements = (
        data.get(
            "elements",
            []
        )
    )


    if not isinstance(
        elements,
        list,
    ):

        raise ValueError(
            "Overpass elements "
            "must be a list"
        )


    if len(elements) == 0:

        print(
            "Primary query returned "
            "0 elements."
        )

        print(
            "Trying fallback query..."
        )


        data = fetch_overpass(
            build_fallback_query(
                province_iso
            )
        )


        elements = (
            data.get(
                "elements",
                []
            )
        )


        if not isinstance(
            elements,
            list,
        ):

            raise ValueError(
                "Fallback elements "
                "must be a list"
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
                province_name,
                province_iso,
                collected_at,
            )
        )


        if normalized is not None:

            records.append(
                normalized
            )


    records = (
        deduplicate_records(
            records
        )
    )


    print(
        "OSM elements =",
        len(elements),
    )

    print(
        "Vegetarian/Vegan records =",
        len(records),
    )


    return records


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    records: list[
        dict[str, Any]
    ],
) -> None:

    vegetarian_confirmed = 0
    vegan_confirmed = 0

    displayable_count = 0
    hidden_count = 0

    coordinate_count = 0


    province_counts: dict[
        str,
        int
    ] = {}


    for item in records:

        if (
            item.get(
                "vegetarian_status"
            )
            ==
            "confirmed"
        ):

            vegetarian_confirmed += 1


        if (
            item.get(
                "vegan_status"
            )
            ==
            "confirmed"
        ):

            vegan_confirmed += 1


        if item.get(
            "displayable"
        ):

            displayable_count += 1

        else:

            hidden_count += 1


        location = (
            item.get(
                "location",
                {}
            )
        )


        if (
            location.get(
                "latitude"
            )
            is not None
            and
            location.get(
                "longitude"
            )
            is not None
        ):

            coordinate_count += 1


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


    print()

    print("=" * 60)

    print(
        "VEGETARIAN DATA SUMMARY"
    )

    print("=" * 60)


    print(
        "Total records =",
        len(records),
    )


    print(
        "Vegetarian confirmed =",
        vegetarian_confirmed,
    )


    print(
        "Vegan confirmed =",
        vegan_confirmed,
    )


    print(
        "Displayable records =",
        displayable_count,
    )


    print(
        "Hidden raw records =",
        hidden_count,
    )


    print(
        "Records with coordinates =",
        coordinate_count,
    )


    print(
        "Province counts =",
        province_counts,
    )


    print(
        "Jay inferred =",
        0,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 60)

    print(
        COLLECTOR_NAME
    )

    print(
        "Version",
        COLLECTOR_VERSION,
    )

    print("=" * 60)


    collected_at = (
        datetime.now()
        .astimezone()
        .isoformat()
    )


    records: list[
        dict[str, Any]
    ] = []


    for province_name in (
        ACTIVE_PROVINCES
    ):

        province_config = (
            PROVINCES.get(
                province_name
            )
        )


        if province_config is None:

            raise ValueError(
                "Unknown province: "
                f"{province_name}"
            )


        province_records = (
            collect_province(
                province_name,
                province_config,
                collected_at,
            )
        )


        records.extend(
            province_records
        )


    records = (
        deduplicate_records(
            records
        )
    )


    records.sort(
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
                    "name"
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


    validate_records(
        records
    )


    save_json(
        OUTPUT_FILE,
        records,
    )


    print_summary(
        records
    )


    print()

    print(
        "Saved:",
        OUTPUT_FILE,
    )


    print()

    if len(records) == 0:

        print(
            "NOTICE:"
        )

        print(
            "No vegetarian/vegan "
            "OSM evidence found."
        )


    print()

    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":

    main()
