from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# PRACHINLIFE
# Vegetarian / Vegan Collector V2
#
# Strategy:
# - ไม่ query ทั้งประเทศไทยครั้งเดียว
# - query ทีละจังหวัด
# - retry เมื่อ connection มีปัญหา
# - จังหวัดหนึ่งพัง ไม่ทำให้ทั้งงานพัง
# - merge ผลลัพธ์ก่อนเขียน JSON
# ============================================================


# ============================================================
# CONFIG
# ============================================================

OUTPUT_FILE = Path("vegetarian_index.json")

REQUEST_TIMEOUT = 45

MAX_RETRIES = 2

SLEEP_BETWEEN_REQUESTS = 2


# ใช้มากกว่า 1 endpoint
# ถ้า endpoint แรกมีปัญหา จะลอง endpoint ถัดไป
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


# ============================================================
# PROVINCES V1
#
# เริ่มจากจังหวัดใกล้ปราจีนบุรี + กรุงเทพฯ ก่อน
# เมื่อระบบ PASS แล้วค่อยเพิ่มจังหวัดอื่น
# ============================================================

PROVINCES = [
    "ปราจีนบุรี",
    "นครนายก",
    "ฉะเชิงเทรา",
    "ชลบุรี",
    "กรุงเทพมหานคร",
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

    try:

        if latitude is None or longitude is None:
            return None, None

        return (
            float(latitude),
            float(longitude),
        )

    except (TypeError, ValueError):

        return None, None


# ============================================================
# FOOD TYPES
# ============================================================

def get_food_types(tags):
    food_types = []

    vegetarian_value = clean_text(
        tags.get("diet:vegetarian")
    )

    vegan_value = clean_text(
        tags.get("diet:vegan")
    )

    if vegetarian_value in {
        "yes",
        "only",
    }:

        food_types.append(
            "vegetarian"
        )

    if vegan_value in {
        "yes",
        "only",
    }:

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
        "food_court",
    }

    if amenity in allowed:
        return amenity

    return "restaurant"


def get_category_label(tags):
    mapping = {

        "restaurant":
            "ร้านอาหาร",

        "cafe":
            "คาเฟ่",

        "fast_food":
            "อาหารจานด่วน",

        "food_court":
            "ศูนย์อาหาร",
    }

    return mapping.get(
        tags.get("amenity"),
        "อาหารและเครื่องดื่ม",
    )


# ============================================================
# SOURCE URL
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
    province,
):
    return {

        "subdistrict":
            clean_text(
                tags.get(
                    "addr:subdistrict"
                )
            )
            or clean_text(
                tags.get(
                    "addr:suburb"
                )
            ),

        "district":
            clean_text(
                tags.get(
                    "addr:district"
                )
            )
            or clean_text(
                tags.get(
                    "addr:city"
                )
            ),

        "province":
            clean_text(
                tags.get(
                    "addr:province"
                )
            )
            or clean_text(
                tags.get(
                    "addr:state"
                )
            )
            or province,

        "country":
            "TH",

        "latitude":
            latitude,

        "longitude":
            longitude,
    }


# ============================================================
# NORMALIZE
# ============================================================

def normalize_element(
    element,
    province,
):
    tags = (
        element.get("tags")
        or {}
    )

    title = (
        clean_text(
            tags.get("name:th")
        )
        or clean_text(
            tags.get("name")
        )
        or clean_text(
            tags.get("brand")
        )
    )

    # ร้านไม่มีชื่อ ไม่เอาเข้า index
    if not title:
        return None

    food_types = get_food_types(
        tags
    )

    if not food_types:
        return None

    latitude, longitude = (
        get_coordinates(
            element
        )
    )

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

    opening_hours = (
        clean_text(
            tags.get(
                "opening_hours"
            )
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

    cuisine_raw = (
        clean_text(
            tags.get(
                "cuisine"
            )
        )
    )

    cuisine = []

    if cuisine_raw:

        cuisine = [
            value.strip()
            for value
            in cuisine_raw.split(";")
            if value.strip()
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
                province,
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
# QUERY
# ============================================================

def build_query(province):
    return f"""
[out:json][timeout:30];

area
  ["boundary"="administrative"]
  ["admin_level"="4"]
  ["name:th"="{province}"]
  ->.province;

(
  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["diet:vegetarian"~"yes|only"]
    (area.province);

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["diet:vegan"~"yes|only"]
    (area.province);
);

out center tags;
"""


# ============================================================
# FETCH ONE PROVINCE
# ============================================================

def fetch_province(
    province,
):
    query = build_query(
        province
    )

    print()

    print(
        f"[FETCH] {province}"
    )

    last_error = None

    for endpoint in (
        OVERPASS_ENDPOINTS
    ):

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:

                print(
                    f"  endpoint="
                    f"{endpoint}"
                )

                print(
                    f"  attempt="
                    f"{attempt}"
                )

                response = (
                    requests.post(
                        endpoint,
                        data={
                            "data":
                                query
                        },
                        timeout=
                            REQUEST_TIMEOUT,
                        headers={
                            "User-Agent":
                                (
                                    "PrachinLife/"
                                    "VegetarianCollectorV2"
                                )
                        },
                    )
                )

                response.raise_for_status()

                data = response.json()

                elements = (
                    data.get(
                        "elements",
                        [],
                    )
                )

                print(
                    f"  result="
                    f"{len(elements)}"
                )

                return elements

            except (
                requests.RequestException,
                ValueError,
            ) as error:

                last_error = error

                print(
                    "  failed:",
                    str(error),
                )

                time.sleep(2)

    print(
        f"[SKIP] {province}"
    )

    if last_error:

        print(
            "  last_error:",
            str(last_error),
        )

    return []


# ============================================================
# BUILD RECORDS
# ============================================================

def build_records(
    province,
    elements,
):
    records = []

    for element in elements:

        record = normalize_element(
            element,
            province,
        )

        if record:

            records.append(
                record
            )

    return records


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_records(
    records,
):
    unique = {}

    for record in records:

        record_id = record.get(
            "id"
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

def sort_records(
    records,
):
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
# WRITE
# ============================================================

def write_index(
    records,
):
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
        f"Saved "
        f"{len(records)} "
        f"places to "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    records,
):
    vegetarian_count = sum(

        "vegetarian"
        in record.get(
            "food_types",
            [],
        )

        for record
        in records
    )

    vegan_count = sum(

        "vegan"
        in record.get(
            "food_types",
            [],
        )

        for record
        in records
    )

    print()

    print("=" * 60)

    print(
        "SUMMARY"
    )

    print("-" * 60)

    print(
        "Total places =",
        len(records),
    )

    print(
        "Vegetarian =",
        vegetarian_count,
    )

    print(
        "Vegan =",
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
        "Vegetarian Collector V2"
    )

    print("=" * 60)

    all_records = []

    for province in (
        PROVINCES
    ):

        elements = fetch_province(
            province
        )

        records = build_records(
            province,
            elements,
        )

        print(
            f"[FOUND] "
            f"{province} = "
            f"{len(records)} places"
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
        all_records
    )

    write_index(
        all_records
    )

    print()

    print(
        "DONE"
    )


if __name__ == "__main__":
    main()
