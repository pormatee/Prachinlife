from __future__ import annotations

import json
import time
from pathlib import Path

import requests


INPUT = Path(
    "data/candidates/"
    "go_official_web_enrichment_v1.json"
)

OUTPUT = Path(
    "data/candidates/"
    "go_official_candidates_resolved_v1_round3.json"
)

URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent":
        "PrachinLife-GoDiscoveryV1-Round3/1.0"
}


def build_queries(row):
    title = row["title"]
    province = row["province"]
    district = row.get("district")
    subdistrict = row.get("subdistrict")

    queries = []

    if subdistrict and district:
        queries.append(
            f"{title}, {subdistrict}, "
            f"{district}, {province}, ประเทศไทย"
        )

    if district:
        queries.append(
            f"{title}, {district}, "
            f"{province}, ประเทศไทย"
        )

    queries.append(
        f"{title}, {province}, ประเทศไทย"
    )

    return queries


def search(query):
    response = requests.get(
        URL,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 5,
            "countrycodes": "th",
            "addressdetails": 1,
        },
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def main():
    rows = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    results = []

    for index, row in enumerate(rows, 1):
        print(
            f"[{index}/{len(rows)}]",
            row["title"],
        )

        matches = []

        for query in build_queries(row):
            print("  QUERY:", query)

            try:
                found = search(query)
            except Exception as error:
                print("  ERROR:", error)
                time.sleep(1.2)
                continue

            for item in found:
                matches.append({
                    "query": query,
                    "display_name":
                        item.get("display_name"),
                    "latitude":
                        float(item["lat"]),
                    "longitude":
                        float(item["lon"]),
                    "osm_type":
                        item.get("osm_type"),
                    "osm_id":
                        item.get("osm_id"),
                    "category":
                        item.get("category"),
                    "type":
                        item.get("type"),
                    "importance":
                        item.get("importance"),
                    "address":
                        item.get("address") or {},
                })

            if found:
                break

            time.sleep(1.2)

        results.append({
            "title": row["title"],
            "official_evidence": row,
            "resolution_status":
                "matches_found"
                if matches
                else "not_found",
            "matches": matches,
        })

        print("  MATCHES =", len(matches))
        time.sleep(1.2)

    OUTPUT.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
