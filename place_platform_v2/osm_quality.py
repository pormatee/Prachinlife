from __future__ import annotations

import time
from dataclasses import dataclass
import requests

DEFAULT_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

@dataclass(frozen=True)
class GridBox:
    south: float
    west: float
    north: float
    east: float

@dataclass(frozen=True)
class QualityFetchResult:
    elements: tuple[dict, ...]
    completed_boxes: int
    failed_boxes: int
    total_boxes: int
    coverage_complete: bool
    errors: tuple[str, ...]

def build_grid(south, west, north, east, rows=4, cols=4):
    if rows < 1 or cols < 1:
        raise ValueError("rows/cols must be >= 1")
    if not (south < north and west < east):
        raise ValueError("invalid bbox")
    lat_step = (north - south) / rows
    lon_step = (east - west) / cols
    return tuple(
        GridBox(
            south + r * lat_step,
            west + c * lon_step,
            south + (r + 1) * lat_step,
            west + (c + 1) * lon_step,
        )
        for r in range(rows)
        for c in range(cols)
    )

def build_area_bbox_query(iso3166_2, box):
    iso = iso3166_2.strip()
    if not iso:
        raise ValueError("iso3166_2 required")
    bbox = f"{box.south},{box.west},{box.north},{box.east}"
    return (
        "[out:json][timeout:45];\n"
        f'area["boundary"="administrative"]["ISO3166-2"="{iso}"]->.searchArea;\n'
        "(\n"
        f'  nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream|hospital|clinic|pharmacy|bank|atm|fuel|school|college|university|marketplace)$"](area.searchArea)({bbox});\n'
        f'  nwr["shop"](area.searchArea)({bbox});\n'
        f'  nwr["tourism"](area.searchArea)({bbox});\n'
        f'  nwr["healthcare"](area.searchArea)({bbox});\n'
        ");\n"
        "out center tags;"
    )

def dedupe_elements(elements):
    unique = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        key = (element.get("type"), element.get("id"))
        if key[0] and key[1] is not None:
            unique[key] = element
    return tuple(
        unique[k]
        for k in sorted(unique, key=lambda x: (str(x[0]), str(x[1])))
    )

def fetch_one(query, timeout=65, max_retries=2):
    errors = []
    for endpoint in DEFAULT_ENDPOINTS:
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers={
                        "User-Agent": "PrachinLife-DiscoveryV2/2.2",
                        "Accept": "application/json",
                    },
                    timeout=timeout,
                )
                if response.status_code == 429:
                    errors.append(f"{endpoint}:429:a{attempt}")
                    time.sleep(min(4 * attempt, 8))
                    continue
                response.raise_for_status()
                payload = response.json()
                elements = payload.get("elements", [])
                if not isinstance(elements, list):
                    raise ValueError("elements must be list")
                return tuple(elements), endpoint, tuple(errors)
            except (requests.RequestException, ValueError) as exc:
                errors.append(
                    f"{endpoint}:{type(exc).__name__}:{exc}"
                )
                if attempt < max_retries:
                    time.sleep(min(2 * attempt, 4))
    return (), None, tuple(errors)

def fetch_quality_grid(iso3166_2, boxes, timeout=65, max_retries=2):
    elements = []
    errors = []
    complete = 0
    failed = 0
    total = len(boxes)

    for i, box in enumerate(boxes, 1):
        print(
            f"[QUALITY GRID {i}/{total}] "
            f"{box.south:.4f},{box.west:.4f},"
            f"{box.north:.4f},{box.east:.4f}",
            flush=True,
        )
        found, endpoint, box_errors = fetch_one(
            build_area_bbox_query(iso3166_2, box),
            timeout=timeout,
            max_retries=max_retries,
        )
        if endpoint is None:
            failed += 1
            errors.append(f"grid-{i}: " + " | ".join(box_errors))
            print(f"[QUALITY GRID {i}/{total}] FAILED", flush=True)
        else:
            complete += 1
            elements.extend(found)
            print(
                f"[QUALITY GRID {i}/{total}] OK "
                f"elements={len(found)} endpoint={endpoint}",
                flush=True,
            )
        if i < total:
            time.sleep(0.8)

    return QualityFetchResult(
        elements=dedupe_elements(elements),
        completed_boxes=complete,
        failed_boxes=failed,
        total_boxes=total,
        coverage_complete=(failed == 0 and complete == total),
        errors=tuple(errors),
    )
