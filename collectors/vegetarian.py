from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OUTPUT_FILE = Path("vegetarian_index.json")

TIMEOUT_SECONDS = 120


# ============================================================
# OVERPASS QUERY
# Thailand + restaurants/cafes/food places
# with vegetarian / vegan tags
# ============================================================

OVERPASS_QUERY = r"""
[out:json][timeout:90];

area
  ["ISO3166-1"="TH"]
  ["boundary"="administrative"]
  ->.thailand;

(
  nwr
    ["amenity"~"restaurant|cafe|fast_food"]
    ["diet:vegetarian"="only"]
    (area.thailand);

  nwr
    ["amenity"~"restaurant|cafe|fast_food"]
    ["diet:vegan"="only"]
    (area.thailand);
);

out center tags;
"""


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def get_coordinates(element):
    element_type = element.get("type")

    if element_type == "node":
        latitude = element.get("lat")
        longitude = element.get("lon")

    else:
        center = element.get("center") or {}

        latitude = center.get("lat")
        longitude = center.get("lon")

    if latitude is None or longitude is None:
        return None, None

    try:
        return float(latitude), float(longitude)

    except (TypeError, ValueError):
        return None, None


def map_food_types(tags):
    food_types = []

    vegetarian_value = clean_text(
        tags.get("diet:vegetarian")
    )

    vegan_value = clean_text(
        tags.get("diet:vegan")
    )

    if vegetarian_value == "only":
        food_types.append("vegetarian")

    if vegan_value == "only":
        food_types.append("vegan")

    return food_types


def get_category(tags):
    amenity = clean_text(
        tags.get("amenity")
    )

    mapping = {
        "restaurant": "restaurant",
        "cafe": "cafe",
        "fast_food": "fast_food",
        "food_court": "food_court",
    }

    return mapping.get(
        amenity,
        "restaurant",
    )


def get_category_label(tags):
    amenity = clean_text(
        tags.get("amenity")
    )

    mapping = {
        "restaurant": "ร้านอาหาร",
        "cafe": "คาเฟ่",
        "fast_food": "อาหารจานด่วน",
        "food_court": "ศูนย์อาหาร",
    }

    return mapping.get(
        amenity,
        "อาหารและเครื่องดื่ม",
    )


def build_location(tags, latitude, longitude):
    return {
        "subdistrict": (
            clean_text(tags.get("addr:subdistrict"))
            or clean_text(tags.get("addr:suburb"))
        ),

        "district": (
            clean_text(tags.get("addr:district"))
            or clean_text(tags.get("addr:city"))
        ),

        "province": (
            clean_text(tags.get("addr:province"))
            or clean_text(tags.get("addr:state"))
        ),

        "country": (
            clean_text(tags.get("addr:country"))
            or "TH"
        ),

        "latitude": latitude,
        "longitude": longitude,
    }


def build_source_url(
    element_type,
    osm_id,
):
    if (
        not element_type
        or not osm_id
    ):
        return None

    return (
        "https://www.openstreetmap.org/"
        f"{element_type}/{osm_id}"
    )


# ============================================================
# NORMALIZE
# ============================================================

def normalize_element(element):
    tags = element.get("tags") or {}

    name = (
        clean_text(tags.get("name:th"))
        or clean_text(tags.get("name"))
        or clean_text(tags.get("brand"))
    )

    if not name:
        return None

    food_types = map_food_types(tags)

    if not food_types:
        return None

    latitude, longitude = get_coordinates(
        element
    )

    osm_id = element.get("id")

    element_type = element.get("type")

    source_url = build_source_url(
        element_type,
        osm_id,
    )

    opening_hours = clean_text(
        tags.get("opening_hours")
    )

    phone = (
        clean_text(tags.get("contact:phone"))
        or clean_text(tags.get("phone"))
    )

    website = (
        clean_text(tags.get("contact:website"))
        or clean_text(tags.get("website"))
    )

    cuisine_raw = clean_text(
        tags.get("cuisine")
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
        "id": (
            f"osm-{element_type}-{osm_id}"
        ),

        "title": name,

        "content_type": "vegetarian",

        "category": get_category(
            tags
        ),

        "food_types": food_types,

        "location": build_location(
            tags,
            latitude,
            longitude,
        ),

        "metadata": {
            "category_label":
                get_category_label(tags),

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
# FETCH
# ============================================================

def fetch_osm_data():
    print(
        "Fetching vegetarian / vegan places "
        "from OpenStreetMap..."
    )

    response = requests.post(
        OVERPASS_URL,
        data={
            "data": OVERPASS_QUERY,
        },
        timeout=TIMEOUT_SECONDS,
        headers={
            "User-Agent":
                "PrachinLife/1.0 "
                "(vegetarian data collector)",
        },
    )

    response.raise_for_status()

    data = response.json()

    elements = data.get(
        "elements",
        [],
    )

    print(
        f"OSM elements received = "
        f"{len(elements)}"
    )

    return elements


# ============================================================
# BUILD INDEX
# ============================================================

def build_index(elements):
    records = []

    seen_ids = set()

    for element in elements:
        record = normalize_element(
            element
        )

        if not record:
            continue

        record_id = record["id"]

        if record_id in seen_ids:
            continue

        seen_ids.add(
            record_id
        )

        records.append(
            record
        )

    records.sort(
        key=lambda item:
            (
                str(
                    item.get("location", {})
                    .get("province")
                    or ""
                ),
                str(
                    item.get("title")
                    or ""
                ),
            )
    )

    return records


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

        file.write("\n")

    print(
        f"Saved {len(records)} places "
        f"to {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)

    print(
        "PrachinLife "
        "Vegetarian Collector V1"
    )

    print("=" * 60)

    elements = fetch_osm_data()

    records = build_index(
        elements
    )

    vegetarian_count = sum(
        "vegetarian"
        in item.get(
            "food_types",
            [],
        )
        for item in records
    )

    vegan_count = sum(
        "vegan"
        in item.get(
            "food_types",
            [],
        )
        for item in records
    )

    print(
        f"Vegetarian = "
        f"{vegetarian_count}"
    )

    print(
        f"Vegan = "
        f"{vegan_count}"
    )

    write_index(
        records
    )

    print("=" * 60)

    print(
        "DONE"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
