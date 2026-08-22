from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


REQUEST_TIMEOUT = 45
MAX_RETRIES = 2

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


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


def build_query(province):
    return f"""
[out:json][timeout:40];

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

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["name"~"เจ|มังสวิรัติ|vegetarian|vegan",i]
    (area.province);

  nwr
    ["amenity"~"restaurant|cafe|fast_food|food_court"]
    ["name:th"~"เจ|มังสวิรัติ",i]
    (area.province);
);

out center tags;
"""


def fetch(province):
    query = build_query(province)

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(
                    f"[FETCH] {endpoint} attempt={attempt}"
                )

                response = requests.post(
                    endpoint,
                    data={"data": query},
                    timeout=REQUEST_TIMEOUT,
                    headers={
                        "User-Agent":
                            "PrachinLife-VegetarianDiscoveryV2/1.0"
                    },
                )

                response.raise_for_status()

                data = response.json()

                elements = data.get(
                    "elements",
                    [],
                )

                print(
                    "RECEIVED =",
                    len(elements),
                )

                return elements

            except (
                requests.RequestException,
                ValueError,
            ) as error:

                print(
                    "FAILED =",
                    error,
                )

                time.sleep(2)

    return []


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

    keyword_match = any(
        keyword in name_lower
        for keyword in [
            "เจ",
            "มังสวิรัติ",
            "vegetarian",
            "vegan",
        ]
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
