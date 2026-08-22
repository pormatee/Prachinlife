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
class GridFetchResult:
    elements: tuple[dict, ...]
    completed_boxes: int
    failed_boxes: int
    total_boxes: int
    coverage_complete: bool
    errors: tuple[str, ...]

def build_grid(south, west, north, east, rows=3, cols=3):
    if rows < 1 or cols < 1:
        raise ValueError("rows/cols must be >= 1")
    if not (south < north and west < east):
        raise ValueError("invalid bounding box")
    lat_step = (north - south) / rows
    lon_step = (east - west) / cols
    boxes = []
    for r in range(rows):
        for c in range(cols):
            boxes.append(GridBox(
                south + r * lat_step,
                west + c * lon_step,
                south + (r + 1) * lat_step,
                west + (c + 1) * lon_step,
            ))
    return tuple(boxes)

def build_bbox_query(box):
    bbox = f"{box.south},{box.west},{box.north},{box.east}"
    return (
        "[out:json][timeout:45];\n"
        "(\n"
        f'  nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream|hospital|clinic|pharmacy|bank|atm|fuel|school|college|university|marketplace)$"]({bbox});\n'
        f'  nwr["shop"]({bbox});\n'
        f'  nwr["tourism"]({bbox});\n'
        f'  nwr["healthcare"]({bbox});\n'
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
    return tuple(unique[k] for k in sorted(unique, key=lambda x: (str(x[0]), str(x[1]))))

def fetch_one(query, *, timeout=65, max_retries=2, endpoints=DEFAULT_ENDPOINTS):
    errors = []
    for endpoint in endpoints:
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    timeout=timeout,
                    headers={
                        "User-Agent": "PrachinLife-DiscoveryV2/2.1",
                        "Accept": "application/json",
                    },
                )
                if response.status_code == 429:
                    errors.append(f"{endpoint}:429:a{attempt}")
                    time.sleep(min(5 * attempt, 10))
                    continue
                response.raise_for_status()
                payload = response.json()
                elements = payload.get("elements", [])
                if not isinstance(elements, list):
                    raise ValueError("elements must be list")
                return tuple(elements), endpoint, tuple(errors)
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{endpoint}:{type(exc).__name__}:{exc}")
                if attempt < max_retries:
                    time.sleep(min(2 * attempt, 5))
    return (), None, tuple(errors)

def fetch_grid(boxes, *, timeout=65, max_retries=2, sleep_seconds=1.0):
    all_elements = []
    errors = []
    completed = 0
    failed = 0
    total = len(boxes)

    for index, box in enumerate(boxes, start=1):
        print(
            f"[GRID {index}/{total}] "
            f"{box.south:.4f},{box.west:.4f},{box.north:.4f},{box.east:.4f}",
            flush=True,
        )
        elements, endpoint, box_errors = fetch_one(
            build_bbox_query(box),
            timeout=timeout,
            max_retries=max_retries,
        )
        if endpoint is None:
            failed += 1
            errors.append(f"grid-{index}: " + " | ".join(box_errors))
            print(f"[GRID {index}/{total}] FAILED", flush=True)
        else:
            completed += 1
            all_elements.extend(elements)
            print(
                f"[GRID {index}/{total}] OK elements={len(elements)} endpoint={endpoint}",
                flush=True,
            )
        if index < total:
            time.sleep(sleep_seconds)

    return GridFetchResult(
        elements=dedupe_elements(all_elements),
        completed_boxes=completed,
        failed_boxes=failed,
        total_boxes=total,
        coverage_complete=(failed == 0 and completed == total),
        errors=tuple(errors),
    )
