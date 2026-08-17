from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# PRACHINLIFE
# Vegetarian Collector V3
#
# Strategy
# - Strict vegetarian / vegan only
# - Thailand split into 8 bounding-box regions
# - Multiple Overpass endpoints
# - Retry + fail-safe
# - Deduplicate before write
# - Never overwrite existing index if all requests fail
# ============================================================


# ============================================================
# CONFIG
# ============================================================

OUTPUT_FILE = Path("vegetarian_index.json")

REQUEST_TIMEOUT = 40

MAX_RETRIES = 2

SLEEP_BETWEEN_REQUESTS = 1.0


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


# ============================================================
# THAILAND REGIONS
#
# bbox format:
# south, west, north, east
#
# intentionally slightly overlapping
# deduplicate by OSM ID afterwards
# ============================================================

REGIONS = [
    {
        "name": "North-West",
        "bbox": (17.0, 97.2, 20.6, 101.8),
    },
    {
        "name": "North-East",
        "bbox": (17.0, 101.5, 20.6, 105.8),
    },
    {
        "name": "Upper-Central-West",
        "bbox": (14.5, 97.2, 17.3, 101.8),
    },
    {
        "name": "Upper-Central-East",
        "bbox": (14.5, 101.5, 17.3, 105.8),
    },
    {
        "name": "Lower-Central-West",
        "bbox": (11.5, 97.2, 14.8, 101.8),
    },
    {
        "name": "Lower-Central-East",
        "bbox": (11.5, 101.5, 14.8, 105.8),
    },
    {
        "name": "South-Upper",
        "bbox": (8.0, 97.0, 11.8, 103.5),
    },
    {
        "name": "South-Lower",
        "bbox": (5.4, 97.0, 8.3, 103.5),
    },
]


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def get_coordinates(element):
    if element.get("type") == "node":

        latitude = element.get("lat")
        longitude = element.get("lon")

    else:

        center = element.get("center") or {}

        latitude = center.get("lat")
        longitude = center.get("lon")

    if latitude is None or longitude is None:
        return None, None

    try:
        return (
            float(latitude),
            float(longitude),
        )

    except (TypeError, ValueError):
        return None, None


# ============================================================
# STRICT FOOD TYPE
# ============================================================

def get_food_types(tags):
    food_types = []

    vegetarian_value = clean_text(
        tags.get("diet:vegetarian")
    )

    vegan_value = clean_text(
        tags.get("diet:vegan")
    )

    # Strict only:
    # "yes" is NOT enough for PrachinLife
    if vegetarian_value == "only":
        food_types.append(
            "vegetarian"
        )

    if vegan_value == "only":
        food_types.append(
            "vegan"
        )

    return food_types


# ============================================================
# CATEGORY
# ============================================================

def get_category(tags):
    amenity = clean_text(
        tags.get("amenity")
    )

    allowed = {
        "restaurant",
        "cafe",
        "fast_food",
    }

    if amenity in allowed:
        return amenity

    return "restaurant"


def get_category_label(tags):
    mapping = {
        "restaurant": "ร้านอาหาร",
        "cafe": "คาเฟ่",
        "fast_food": "อาหารจานด่วน",
    }

    return mapping.get(
        tags.get("amenity"),
        "ร้านอาหาร",
    )


# ============================================================
# SOURCE
# ============================================================

def build_source_url(
    element_type,
    osm_id,
):
    if (
        not element_type
        or osm_id is None
    ):
        return None

    return (
        "https://www.openstreetmap.org/"
        f"{element_type}/{osm_id}"
    )


# ============================================================
# LOCATION
# ============================================================

def build_location(
    tags,
    latitude,
    longitude,
):
    return {
        "subdistrict": (
            clean_text(
                tags.get("addr:subdistrict")
            )
            or
            clean_text(
                tags.get("addr:suburb")
            )
        ),

        "district": (
            clean_text(
                tags.get("addr:district")
            )
            or
            clean_text(
                tags.get("addr:city")
            )
        ),

        "province": (
            clean_text(
                tags.get("addr:province")
            )
            or
            clean_text(
                tags.get("addr:state")
            )
        ),

        "country": "TH",

        "latitude": latitude,

        "longitude": longitude,
    }


# ============================================================
# QUERY
# ============================================================

def build_query(bbox):
    south, west, north, east = bbox

    return f"""
[out:json][timeout:25];

(
  nwr
    ["amenity"~"restaurant|cafe|fast_food"]
    ["diet:vegetarian"="only"]
    ({south},{west},{north},{east});

  nwr
    ["amenity"~"restaurant|cafe|fast_food"]
    ["diet:vegan"="only"]
    ({south},{west},{north},{east});
);

out center tags;
"""


# ============================================================
# FETCH REGION
# ============================================================

def fetch_region(region):
    region_name = region["name"]

    query = build_query(
        region["bbox"]
    )

    print()
    print(
        f"[FETCH] {region_name}"
    )

    last_error = None


    for endpoint in OVERPASS_ENDPOINTS:

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:

                print(
                    f"  endpoint = {endpoint}"
                )

                print(
                    f"  attempt  = {attempt}"
                )


                response = requests.post(
                    endpoint,

                    data={
                        "data": query,
                    },

                    headers={
                        "User-Agent":
                            "PrachinLife-VegetarianCollector/3.0"
                    },

                    timeout=
                        REQUEST_TIMEOUT,
                )


                response.raise_for_status()


                data = response.json()


                elements = data.get(
                    "elements",
                    [],
                )


                print(
                    f"  received = "
                    f"{len(elements)}"
                )


                return (
                    elements,
                    True,
                )


            except (
                requests.RequestException,
                ValueError,
            ) as error:

                last_error = error


                print(
                    "  failed =",
                    str(error),
                )


                time.sleep(2)


    print(
        f"[SKIP] {region_name}"
    )


    if last_error:

        print(
            "  last error =",
            str(last_error),
        )


    return (
        [],
        False,
    )


# ============================================================
# NORMALIZE
# ============================================================

def normalize_element(element):
    tags = (
        element.get("tags")
        or {}
    )


    title = (
        clean_text(
            tags.get("name:th")
        )
        or
        clean_text(
            tags.get("name")
        )
        or
        clean_text(
            tags.get("brand")
        )
    )


    # No usable shop name
    if not title:
        return None


    food_types = get_food_types(
        tags
    )


    # Must satisfy strict "only"
    if not food_types:
        return None


    latitude, longitude = (
        get_coordinates(
            element
        )
    )


    # PrachinLife needs coordinates
    # for Near Me
    if (
        latitude is None
        or longitude is None
    ):
        return None


    element_type = (
        element.get("type")
    )


    osm_id = (
        element.get("id")
    )


    source_url = (
        build_source_url(
            element_type,
            osm_id,
        )
    )


    opening_hours = clean_text(
        tags.get(
            "opening_hours"
        )
    )


    phone = (
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
    )


    website = (
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
    )


    cuisine_raw = clean_text(
        tags.get(
            "cuisine"
        )
    )


    cuisine = []

    if cuisine_raw:

        cuisine = [
            item.strip()
            for item
            in cuisine_raw.split(";")
            if item.strip()
        ]


    return {
        "id":
            f"osm-{element_type}-{osm_id}",

        "title":
            title,

        "content_type":
            "vegetarian",

        "category":
            get_category(
                tags
            ),

        "food_types":
            food_types,

        "location":
            build_location(
                tags,
                latitude,
                longitude,
            ),

        "metadata": {
            "category_label":
                get_category_label(
                    tags
                ),

            "opening_hours":
                opening_hours,

            "phone":
                phone,

            "website":
                website,

            "cuisine":
                cuisine,

            "diet_vegetarian":
                clean_text(
                    tags.get(
                        "diet:vegetarian"
                    )
                ),

            "diet_vegan":
                clean_text(
                    tags.get(
                        "diet:vegan"
                    )
                ),

            "source_name":
                "OpenStreetMap",

            "source_url":
                source_url,

            "verified":
                True,
        },

        "source":
            "OpenStreetMap",

        "source_url":
            source_url,

        "collected_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# ============================================================
# BUILD RECORDS
# ============================================================

def build_records(elements):
    records = []

    for element in elements:

        record = normalize_element(
            element
        )

        if record:

            records.append(
                record
            )

    return records


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_records(records):
    unique = {}

    for record in records:

        record_id = (
            record.get("id")
        )

        if not record_id:
            continue

        unique[
            record_id
        ] = record


    return list(
        unique.values()
    )


# ============================================================
# SORT
# ============================================================

def sort_records(records):
    return sorted(
        records,

        key=lambda item: (
            str(
                item
                .get(
                    "location",
                    {}
                )
                .get(
                    "province"
                )
                or ""
            ),

            str(
                item.get(
                    "title"
                )
                or ""
            ),
        )
    )


# ============================================================
# EXISTING FILE SAFETY
# ============================================================

def load_existing_records():
    if not OUTPUT_FILE.exists():

        return []


    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )


        if isinstance(
            data,
            list,
        ):

            return data


    except Exception as error:

        print(
            "[WARN] Existing index read error:",
            error,
        )


    return []


# ============================================================
# WRITE
# ============================================================

def write_index(records):
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write(
            "\n"
        )


    print()

    print(
        f"Saved {len(records)} places "
        f"to {OUTPUT_FILE}"
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    records,
    success_count,
    failed_count,
):
    vegetarian_count = sum(
        "vegetarian"
        in item.get(
            "food_types",
            [],
        )

        for item
        in records
    )


    vegan_count = sum(
        "vegan"
        in item.get(
            "food_types",
            [],
        )

        for item
        in records
    )


    print()

    print("=" * 60)

    print(
        "SUMMARY"
    )

    print("-" * 60)

    print(
        "Successful regions =",
        success_count,
    )

    print(
        "Failed regions =",
        failed_count,
    )

    print(
        "Total strict places =",
        len(records),
    )

    print(
        "Vegetarian only =",
        vegetarian_count,
    )

    print(
        "Vegan only =",
        vegan_count,
    )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)

    print(
        "PrachinLife "
        "Vegetarian Collector V3"
    )

    print("=" * 60)

    print(
        "Strict policy:"
    )

    print(
        "- vegetarian=only"
    )

    print(
        "- vegan=only"
    )

    print(
        "- no food court"
    )

    print(
        "- 8 Thailand regions"
    )

    print("=" * 60)


    existing_records = (
        load_existing_records()
    )


    all_records = []

    success_count = 0

    failed_count = 0


    total_regions = len(
        REGIONS
    )


    for index, region in enumerate(
        REGIONS,
        start=1,
    ):

        print()

        print(
            f"[{index}/{total_regions}] "
            f"{region['name']}"
        )


        elements, success = (
            fetch_region(
                region
            )
        )


        if not success:

            failed_count += 1

            continue


        success_count += 1


        records = build_records(
            elements
        )


        print(
            f"[FOUND] "
            f"{region['name']} = "
            f"{len(records)}"
        )


        all_records.extend(
            records
        )


        time.sleep(
            SLEEP_BETWEEN_REQUESTS
        )


    all_records = (
        deduplicate_records(
            all_records
        )
    )


    all_records = (
        sort_records(
            all_records
        )
    )


    print_summary(
        all_records,
        success_count,
        failed_count,
    )


    # ========================================================
    # SAFETY 1
    # all requests failed
    # ========================================================

    if success_count == 0:

        print()

        print(
            "[ABORT WRITE]"
        )

        print(
            "All Overpass regions failed."
        )

        print(
            f"Existing index preserved: "
            f"{len(existing_records)} places"
        )

        return


    # ========================================================
    # SAFETY 2
    # requests succeeded but nothing strict found
    # ========================================================

    if len(all_records) == 0:

        print()

        print(
            "[ABORT WRITE]"
        )

        print(
            "No strict vegetarian / vegan "
            "places found."
        )

        print(
            f"Existing index preserved: "
            f"{len(existing_records)} places"
        )

        return


    write_index(
        all_records
    )


    print()

    print(
        "DONE"
    )


if __name__ == "__main__":
    main()
