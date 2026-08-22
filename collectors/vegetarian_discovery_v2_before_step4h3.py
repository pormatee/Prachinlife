from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
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

import requests

from scripts.place_discovery_location import (
    get_province_config,
    split_bbox,
)

from scripts.place_discovery_osm import (
    fetch_overpass_query,
    fetch_bbox_grid,
)


REQUEST_TIMEOUT = 45
MAX_RETRIES = 2

SLEEP_BETWEEN_GRID_REQUESTS = 1.5
RATE_LIMIT_BACKOFF_SECONDS = 8

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

PROVINCE_CONFIG_FILE = Path(
    "data/config/thailand_provinces.json"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="PrachinLife Vegetarian Discovery V2"
    )

    parser.add_argument(
        "--province",
        required=True,
        help="Thai province name, e.g. ฉะเชิงเทรา",
    )

    return parser.parse_args()


def build_output_file(province):
    safe_name = (
        province.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    return Path(
        "data/test"
    ) / f"{safe_name}_vegetarian_discovery_v2.json"


def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def get_coordinates(element):
    if element.get("type") == "node":
        lat = element.get("lat")
        lon = element.get("lon")
    else:
        center = element.get("center") or {}
        lat = center.get("lat")
        lon = center.get("lon")

    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None


def load_province_config(province):
    config = get_province_config(
        province
    )

    return {
        "aliases":
            config["aliases"],
        "bbox":
            config["bbox"],
    }


def build_area_query(
    name_field,
    province_name,
):
    return f"""
[out:json][timeout:30];

area
  ["boundary"="administrative"]
  ["admin_level"="4"]
  ["{name_field}"="{province_name}"]
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

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["name"~"อาหารเจ|ร้านเจ|ข้าวเจ|โรงเจ|เจจริง|เจแท้|มังสวิรัติ|vegetarian|vegan",i]
    (area.province);

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["name:th"~"อาหารเจ|ร้านเจ|ข้าวเจ|โรงเจ|เจจริง|เจแท้|มังสวิรัติ",i]
    (area.province);
);

out center tags;
"""


def build_bbox_query(bbox):
    south, west, north, east = bbox

    return f"""
[out:json][timeout:30];

(
  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["diet:vegetarian"~"yes|only"]
    ({south},{west},{north},{east});

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["diet:vegan"~"yes|only"]
    ({south},{west},{north},{east});

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["name"~"อาหารเจ|ร้านเจ|ข้าวเจ|โรงเจ|เจจริง|เจแท้|มังสวิรัติ|vegetarian|vegan",i]
    ({south},{west},{north},{east});

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["name:th"~"อาหารเจ|ร้านเจ|ข้าวเจ|โรงเจ|เจจริง|เจแท้|มังสวิรัติ",i]
    ({south},{west},{north},{east});
);

out center tags;
"""


def fetch(province):
    config = load_province_config(
        province
    )

    common_kwargs = {
        "endpoints":
            OVERPASS_ENDPOINTS,
        "timeout":
            REQUEST_TIMEOUT,
        "max_retries":
            MAX_RETRIES,
        "rate_limit_backoff_seconds":
            RATE_LIMIT_BACKOFF_SECONDS,
        "user_agent":
            "PrachinLife-VegetarianDiscoveryV2/3.0",
    }

    # 1. Thai OSM area name
    elements, success = fetch_overpass_query(
        build_area_query(
            "name:th",
            province,
        ),
        "area:name:th",
        **common_kwargs,
    )

    if elements:
        print(
            "DISCOVERY METHOD = area:name:th"
        )
        return elements

    # 2. English / alternate aliases
    for alias in config["aliases"]:
        elements, success = fetch_overpass_query(
            build_area_query(
                "name",
                alias,
            ),
            f"area:alias:{alias}",
            **common_kwargs,
        )

        if elements:
            print(
                "DISCOVERY METHOD =",
                f"area:alias:{alias}",
            )
            return elements

    # 3. BBox/Grid fallback through shared OSM Core
    grid_boxes = split_bbox(
        config["bbox"],
        rows=2,
        cols=2,
    )

    result = fetch_bbox_grid(
        grid_boxes,
        build_bbox_query,
        sleep_between_requests=
            SLEEP_BETWEEN_GRID_REQUESTS,
        **common_kwargs,
    )

    print(
        "DISCOVERY METHOD = bbox-grid"
        if result.completed_requests > 0
        else
        "DISCOVERY METHOD = none"
    )

    print(
        "GRID UNIQUE =",
        len(result.elements),
    )

    print(
        "GRID COMPLETED =",
        result.completed_requests,
    )

    print(
        "GRID FAILED =",
        result.failed_requests,
    )

    print(
        "COVERAGE COMPLETE =",
        result.coverage_complete,
    )

    if not result.coverage_complete:
        print(
            "WARNING: discovery coverage is incomplete"
        )

    if (
        result.completed_requests == 0
        and
        not result.elements
    ):
        print(
            "WARNING: provider failed for all grids; "
            "0 results must not be interpreted as no places."
        )

    return result.elements
def classify(tags):
    name = (
        clean_text(tags.get("name:th"))
        or clean_text(tags.get("name"))
        or clean_text(tags.get("brand"))
    )

    vegetarian = clean_text(
        tags.get("diet:vegetarian")
    )

    vegan = clean_text(
        tags.get("diet:vegan")
    )

    name_lower = (name or "").lower()

    strong_keywords = [
        "อาหารเจ",
        "ข้าวเจ",
        "โรงเจ",
        "เจจริง",
        "เจแท้",
        "มังสวิรัติ",
        "vegetarian",
        "vegan",
    ]

    strong_match = any(
        keyword in name_lower
        for keyword in strong_keywords
    )

    # "ร้านเจ" ต้องเป็นความหมายอาหารเจจริง
    # ไม่ให้จับคำอย่าง ร้านเจ๊ / เจ้า / เจริญ
    jay_shop_match = bool(
        re.search(
            r"ร้าน\s*เจ(?![่้๊๋า-ูเ-์])",
            name_lower,
        )
    )

    keyword_match = (
        strong_match
        or jay_shop_match
    )

    if vegetarian == "only" or vegan == "only":
        tier = "dedicated"

    elif keyword_match:
        tier = "named_candidate"

    elif vegetarian == "yes" or vegan == "yes":
        tier = "option_available"

    else:
        tier = "unknown"

    return (
        name,
        vegetarian,
        vegan,
        keyword_match,
        tier,
    )


def normalize(element, province):
    tags = element.get("tags") or {}

    (
        name,
        vegetarian,
        vegan,
        keyword_match,
        tier,
    ) = classify(tags)

    if not name:
        return None

    if tier == "unknown":
        return None

    lat, lon = get_coordinates(element)

    element_type = element.get("type")
    osm_id = element.get("id")

    return {
        "id": f"osm-{element_type}-{osm_id}",
        "title": name,
        "content_type": "vegetarian",
        "food_types": [
            item
            for item, yes in [
                (
                    "vegetarian",
                    vegetarian in {"yes", "only"},
                ),
                (
                    "vegan",
                    vegan in {"yes", "only"},
                ),
            ]
            if yes
        ],
        "location": {
            "province": province,
            "district":
                clean_text(tags.get("addr:district"))
                or clean_text(tags.get("addr:city")),
            "subdistrict":
                clean_text(tags.get("addr:subdistrict"))
                or clean_text(tags.get("addr:suburb")),
            "country": "TH",
            "latitude": lat,
            "longitude": lon,
        },
        "metadata": {
            "display_tier": tier,
            "show_in_primary_directory":
                tier in {
                    "dedicated",
                    "named_candidate",
                },
            "needs_review":
                tier == "named_candidate",
            "diet_vegetarian": vegetarian,
            "diet_vegan": vegan,
            "keyword_match": keyword_match,
            "opening_hours":
                clean_text(tags.get("opening_hours")),
            "phone":
                clean_text(tags.get("phone"))
                or clean_text(tags.get("contact:phone")),
            "website":
                clean_text(tags.get("website"))
                or clean_text(tags.get("contact:website")),
        },
        "source": "OpenStreetMap",
        "source_url":
            f"https://www.openstreetmap.org/{element_type}/{osm_id}",
        "collected_at":
            datetime.now(timezone.utc).isoformat(),
    }


def main():
    args = parse_args()

    province = args.province.strip()

    if not province:
        raise SystemExit(
            "ERROR: province must not be empty"
        )

    output_file = build_output_file(
        province
    )

    elements = fetch(
        province
    )

    records = []

    for element in elements:
        record = normalize(element, province)

        if record:
            records.append(record)

    unique = {
        record["id"]: record
        for record in records
    }

    records = list(unique.values())

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        json.dumps(
            records,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("VEGETARIAN DISCOVERY V2")
    print("=" * 60)
    print("Province =", province)
    print("Total =", len(records))

    tiers = {}

    for record in records:
        tier = record["metadata"]["display_tier"]
        tiers[tier] = tiers.get(tier, 0) + 1

    print("Tiers =", tiers)

    print()
    print("RESULTS")

    for record in records:
        print(
            record["metadata"]["display_tier"],
            "|",
            record["title"],
            "| veg =",
            record["metadata"]["diet_vegetarian"],
            "| vegan =",
            record["metadata"]["diet_vegan"],
        )

    print()
    print("Saved =", output_file)


if __name__ == "__main__":
    main()
