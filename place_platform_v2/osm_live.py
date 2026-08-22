from __future__ import annotations
import time
from dataclasses import dataclass
import requests

DEFAULT_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

@dataclass(frozen=True)
class OSMFetchReport:
    elements: tuple[dict, ...]
    endpoint: str
    attempts: int
    coverage_complete: bool

def build_province_place_query(iso3166_2: str) -> str:
    iso = iso3166_2.strip()
    if not iso:
        raise ValueError("iso3166_2 is required")
    return f'''[out:json][timeout:120];
area["boundary"="administrative"]["ISO3166-2"="{iso}"]->.searchArea;
(
  nwr["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream|hospital|clinic|pharmacy|bank|atm|fuel|school|college|university|marketplace)$"](area.searchArea);
  nwr["shop"](area.searchArea);
  nwr["tourism"](area.searchArea);
  nwr["healthcare"](area.searchArea);
);
out center tags;'''

def dedupe_elements(elements):
    unique = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        key = (element.get("type"), element.get("id"))
        if key[0] and key[1] is not None:
            unique[key] = element
    return tuple(
        unique[key]
        for key in sorted(unique, key=lambda item: (str(item[0]), str(item[1])))
    )

def fetch_overpass(
    query: str,
    *,
    endpoints=DEFAULT_ENDPOINTS,
    timeout=150,
    max_retries=2,
    user_agent="PrachinLife-DiscoveryV2/2.0",
):
    if not query.strip():
        raise ValueError("query is required")
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    attempt_count = 0
    errors = []

    for endpoint in endpoints:
        for attempt in range(1, max_retries + 1):
            attempt_count += 1
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers={
                        "User-Agent": user_agent,
                        "Accept": "application/json",
                    },
                    timeout=timeout,
                )
                if response.status_code == 429:
                    errors.append(f"{endpoint}: HTTP 429 attempt={attempt}")
                    time.sleep(min(8 * attempt, 20))
                    continue

                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Overpass response must be an object")
                elements = payload.get("elements", [])
                if not isinstance(elements, list):
                    raise ValueError("Overpass elements must be a list")

                return OSMFetchReport(
                    elements=dedupe_elements(elements),
                    endpoint=endpoint,
                    attempts=attempt_count,
                    coverage_complete=True,
                )
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
                if attempt < max_retries:
                    time.sleep(min(3 * attempt, 10))

    raise RuntimeError("all Overpass endpoints failed: " + " | ".join(errors))
