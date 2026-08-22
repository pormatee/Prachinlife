from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


QUERY_FILE = Path(
    "data/web_discovery/vegetarian_queries.json"
)

OUTPUT_FILE = Path(
    "data/web_discovery/vegetarian_search_results.json"
)

EVIDENCE_FILE = Path(
    "data/web_discovery/google_places_evidence.json"
)

PROVINCE_CONFIG_FILE = Path(
    "data/config/thailand_provinces.json"
)

API_ENDPOINT = (
    "https://"
    "places.googleapis.com/"
    "v1/places:searchText"
)

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.googleMapsUri",
        "places.businessStatus",
        "places.types",
    ]
)

REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_REQUESTS = 0.5


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "PrachinLife Google Places "
            "Vegetarian Adapter V1"
        )
    )

    parser.add_argument(
        "--province",
        required=True,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum results per query",
    )

    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Maximum number of search queries to execute",
    )

    return parser.parse_args()


def load_json(path):
    if not path.exists():
        raise SystemExit(
            f"ERROR: file not found: {path}"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data


def get_bbox(province):
    configs = load_json(
        PROVINCE_CONFIG_FILE
    )

    config = configs.get(
        province
    )

    if not isinstance(
        config,
        dict,
    ):
        raise SystemExit(
            f"ERROR: province not configured: "
            f"{province}"
        )

    bbox = config.get(
        "bbox"
    )

    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
    ):
        raise SystemExit(
            f"ERROR: invalid bbox: "
            f"{province}"
        )

    return bbox


def get_queries(province):
    data = load_json(
        QUERY_FILE
    )

    if not isinstance(data, list):
        raise SystemExit(
            "ERROR: query file must be array"
        )

    queries = [
        item
        for item in data
        if (
            isinstance(item, dict)
            and
            item.get("province")
            == province
            and
            item.get("query")
        )
    ]

    return queries


def build_request_body(
    query,
    bbox,
    limit,
):
    south, west, north, east = bbox

    return {
        "textQuery":
            query,
        "languageCode":
            "th",
        "regionCode":
            "TH",
        "pageSize":
            limit,
        "locationRestriction": {
            "rectangle": {
                "low": {
                    "latitude":
                        south,
                    "longitude":
                        west,
                },
                "high": {
                    "latitude":
                        north,
                    "longitude":
                        east,
                },
            }
        },
    }


def normalize_place(
    place,
    query,
):
    if not isinstance(
        place,
        dict,
    ):
        return None

    display_name = (
        place.get(
            "displayName"
        )
        or {}
    )

    title = (
        display_name.get(
            "text"
        )
        or ""
    ).strip()

    if not title:
        return None

    location = (
        place.get("location")
        or {}
    )

    latitude = location.get(
        "latitude"
    )

    longitude = location.get(
        "longitude"
    )

    maps_url = (
        place.get(
            "googleMapsUri"
        )
        or ""
    )

    formatted_address = (
        place.get(
            "formattedAddress"
        )
        or ""
    )

    return {
        "provider":
            "google_places",
        "provider_place_id":
            place.get("id"),
        "title":
            title,
        "url":
            maps_url,
        "snippet":
            formatted_address,
        "latitude":
            latitude,
        "longitude":
            longitude,
        "source":
            "Google Places",
        "query":
            query,
        "business_status":
            place.get(
                "businessStatus"
            ),
        "types":
            place.get(
                "types"
            )
            or [],
    }



def build_persistent_evidence(
    record,
    province,
):
    return {
        "provider":
            "google_places",
        "place_id":
            record.get(
                "provider_place_id"
            ),
        "province":
            province,
        "query":
            record.get(
                "query"
            ),
        "discovered_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
        "verification_status":
            "discovered",
    }


def main():
    args = parse_args()

    province = (
        args.province
        .strip()
    )

    if not province:
        raise SystemExit(
            "ERROR: province required"
        )

    if (
        args.limit < 1
        or args.limit > 20
    ):
        raise SystemExit(
            "ERROR: limit must be 1-20"
        )

    bbox = get_bbox(
        province
    )

    queries = get_queries(
        province
    )

    if args.max_queries is not None:
        if args.max_queries < 1:
            raise SystemExit(
                "ERROR: max-queries must be >= 1"
            )

        queries = queries[
            :args.max_queries
        ]

    print("=" * 60)
    print(
        "GOOGLE PLACES VEGETARIAN ADAPTER V1"
    )
    print("=" * 60)

    print(
        "Province =",
        province,
    )

    print(
        "Queries =",
        len(queries),
    )

    print(
        "BBox =",
        bbox,
    )

    print(
        "Limit/query =",
        args.limit,
    )

    if not queries:
        raise SystemExit(
            "ERROR: no queries found "
            "for province"
        )

    if args.dry_run:
        print()
        print(
            "DRY RUN - no API requests"
        )

        for item in queries:
            print(
                "-",
                item["query"],
            )

        return

    api_key = os.environ.get(
        "GOOGLE_PLACES_API_KEY"
    )

    if not api_key:
        raise SystemExit(
            "ERROR: GOOGLE_PLACES_API_KEY "
            "environment variable not set"
        )

    headers = {
        "Content-Type":
            "application/json",
        "X-Goog-Api-Key":
            api_key,
        "X-Goog-FieldMask":
            FIELD_MASK,
    }

    collected = []

    failed_queries = []

    for index, item in enumerate(
        queries,
        start=1,
    ):
        query = item["query"]

        print()
        print(
            f"[{index}/{len(queries)}]",
            query,
        )

        body = build_request_body(
            query,
            bbox,
            args.limit,
        )

        try:
            response = requests.post(
                API_ENDPOINT,
                headers=headers,
                json=body,
                timeout=REQUEST_TIMEOUT,
            )

            print(
                "HTTP =",
                response.status_code,
            )

            response.raise_for_status()

            payload = response.json()

            places = payload.get(
                "places",
                [],
            )

            print(
                "RESULTS =",
                len(places),
            )

            for place in places:
                record = normalize_place(
                    place,
                    query,
                )

                if record:
                    collected.append(
                        record
                    )

        except (
            requests.RequestException,
            ValueError,
        ) as error:

            print(
                "FAILED =",
                type(error).__name__,
                str(error),
            )

            failed_queries.append(
                query
            )

        time.sleep(
            SLEEP_BETWEEN_REQUESTS
        )

    # Deduplicate by Google Place ID first.
    unique = {}

    for record in collected:
        key = (
            record.get(
                "provider_place_id"
            )
            or
            (
                record.get(
                    "title",
                    "",
                ).lower(),
                record.get(
                    "latitude"
                ),
                record.get(
                    "longitude"
                ),
            )
        )

        if key not in unique:
            unique[key] = record

    results = list(
        unique.values()
    )

    evidence = []

    seen_place_ids = set()

    for record in results:
        place_id = record.get(
            "provider_place_id"
        )

        if not place_id:
            continue

        if place_id in seen_place_ids:
            continue

        seen_place_ids.add(
            place_id
        )

        evidence.append(
            build_persistent_evidence(
                record,
                province,
            )
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    EVIDENCE_FILE.write_text(
        json.dumps(
            evidence,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(
        "RAW =",
        len(collected),
    )

    print(
        "UNIQUE =",
        len(results),
    )

    print(
        "FAILED QUERIES =",
        len(failed_queries),
    )

    print(
        "PERSISTENT EVIDENCE =",
        len(evidence),
    )

    print(
        "Temporary results =",
        OUTPUT_FILE,
    )

    print(
        "Persistent evidence =",
        EVIDENCE_FILE,
    )


if __name__ == "__main__":
    main()
