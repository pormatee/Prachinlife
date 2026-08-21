from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.place_discovery_location import (
    get_province_config,
    split_bbox,
)
from scripts.place_discovery_osm import (
    fetch_bbox_grid,
)


OUTPUT = Path("service_index.json")

SERVICE_CATEGORIES = {
    "pharmacy": {
        "label": "ร้านยา",
        "osm_tags": [
            ("amenity", "pharmacy"),
        ],
    },

    "clinic": {
        "label": "คลินิก",
        "osm_tags": [
            ("amenity", "clinic"),
        ],
    },

    "fuel": {
        "label": "ปั๊มน้ำมัน",
        "osm_tags": [
            ("amenity", "fuel"),
        ],
    },

    "car_repair": {
        "label": "ซ่อมรถ",
        "osm_tags": [
            ("shop", "car_repair"),
        ],
    },

    "laundry": {
        "label": "ซักรีด",
        "osm_tags": [
            ("shop", "laundry"),
        ],
    },
}


def build_query(
    bbox,
    osm_tags,
) -> str:
    south, west, north, east = bbox

    selectors = []

    for key, value in osm_tags:
        for osm_type in (
            "node",
            "way",
            "relation",
        ):
            selectors.append(
                f'  {osm_type}["{key}"="{value}"]'
                f'({south},{west},{north},{east});'
            )

    body = "\n".join(selectors)

    return f"""
[out:json][timeout:60];
(
{body}
);
out center tags;
"""

def get_coordinates(
    element: dict,
):
    if (
        element.get("lat") is not None
        and element.get("lon") is not None
    ):
        return (
            float(element["lat"]),
            float(element["lon"]),
        )

    center = (
        element.get("center")
        or {}
    )

    if (
        center.get("lat") is not None
        and center.get("lon") is not None
    ):
        return (
            float(center["lat"]),
            float(center["lon"]),
        )

    return None, None


def normalize_element(
    element: dict,
    *,
    province: str,
    category: str,
    category_label: str,
) -> dict | None:
    tags = (
        element.get("tags")
        or {}
    )

    title = (
        tags.get("name")
        or tags.get("name:th")
        or tags.get("name:en")
        or ""
    ).strip()

    if not title:
        return None

    latitude, longitude = get_coordinates(
        element
    )

    if (
        latitude is None
        or longitude is None
    ):
        return None

    osm_type = element.get("type")
    osm_id = element.get("id")

    source_url = (
        f"https://www.openstreetmap.org/"
        f"{osm_type}/{osm_id}"
    )

    phone = (
        tags.get("phone")
        or tags.get("contact:phone")
        or None
    )

    website = (
        tags.get("website")
        or tags.get("contact:website")
        or None
    )

    opening_hours = (
        tags.get("opening_hours")
        or None
    )

    return {
        "id": f"osm-{osm_type}-{osm_id}",
        "title": title,
        "content_type": "service",
        "category": category,
        "tags": [],
        "location": {
            "province": province,
            "district": None,
            "subdistrict": None,
            "country": "TH",
            "latitude": latitude,
            "longitude": longitude,
        },
        "metadata": {
            "category_label": category_label,
            "opening_hours": opening_hours,
            "phone": phone,
            "website": website,
            "verified": False,
            "display_tier": "candidate",
            "show_in_primary_directory": False,
            "needs_review": False,
            "review_reason": None,
        },
        "source": "OpenStreetMap",
        "source_url": source_url,
        "collected_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }


def collect_service_category(
    *,
    province: str,
    category: str,
):
    config = SERVICE_CATEGORIES[
        category
    ]

    province_config = (
        get_province_config(
            province
        )
    )

    bbox = (
        province_config.get("bbox")
        or province_config.get(
            "overpass_bbox"
        )
    )

    if not bbox:
        raise ValueError(
            f"Province bbox missing: "
            f"{province}"
        )

    grid_boxes = split_bbox(
        bbox
    )

    def query_builder(
        grid_bbox,
    ):
        return build_query(
            grid_bbox,
            config["osm_tags"],
        )

    result = fetch_bbox_grid(
        grid_boxes,
        query_builder,
        user_agent=(
            "PrachinLife-ServiceV1/1.0"
        ),
    )

    print(
        "  COVERAGE =",
        result.coverage_complete,
        "| completed =",
        result.completed_requests,
        "| failed =",
        result.failed_requests,
    )

    records = []

    for element in result.elements:
        record = normalize_element(
            element,
            province=province,
            category=category,
            category_label=config["label"],
        )

        if record:
            records.append(record)

    return records

def main():
    province = "ปราจีนบุรี"

    all_records = []

    for category in SERVICE_CATEGORIES:
        print(
            "COLLECT:",
            category
        )

        records = collect_service_category(
            province=province,
            category=category,
        )

        print(
            "  FOUND =",
            len(records)
        )

        all_records.extend(
            records
        )

    deduped = {
        row["id"]: row
        for row in all_records
    }

    final = list(
        deduped.values()
    )

    OUTPUT.write_text(
        json.dumps(
            final,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "SAVED:",
        OUTPUT
    )
    print(
        "TOTAL:",
        len(final)
    )


if __name__ == "__main__":
    main()
