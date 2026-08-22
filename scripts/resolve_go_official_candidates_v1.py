from __future__ import annotations

import json
import time
from pathlib import Path

import requests


INPUT = Path(
    "data/candidates/go_official_candidates_v1.json"
)

OUTPUT = Path(
    "data/candidates/go_official_candidates_resolved_v1.json"
)

USER_AGENT = (
    "PrachinLife-GoDiscoveryV1/1.0 "
    "(local-place-discovery)"
)


def search_place(title: str, province: str):
    queries = [
        f"{title}, {province}, Thailand",
        f"{title}, ปราจีนบุรี, ประเทศไทย",
        f"{title}, Thailand",
    ]

    for query in queries:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 5,
                "countrycodes": "th",
                "addressdetails": 1,
            },
            headers={
                "User-Agent": USER_AGENT,
            },
            timeout=30,
        )

        response.raise_for_status()

        rows = response.json()

        if rows:
            return query, rows

        time.sleep(1.1)

    return None, []


def main():
    candidates = json.loads(
        INPUT.read_text(
            encoding="utf-8"
        )
    )

    resolved = []

    for index, candidate in enumerate(
        candidates,
        1,
    ):
        title = candidate["title"]
        province = candidate["province"]

        print(
            f"[{index}/{len(candidates)}] "
            f"{title}"
        )

        try:
            query, rows = search_place(
                title,
                province,
            )

        except Exception as error:
            print(
                "  ERROR:",
                error,
            )

            resolved.append(
                {
                    **candidate,
                    "resolution_status":
                        "lookup_error",
                    "resolution_error":
                        str(error),
                    "matches": [],
                }
            )

            time.sleep(1.1)
            continue

        matches = []

        for row in rows:
            matches.append(
                {
                    "osm_type":
                        row.get("osm_type"),

                    "osm_id":
                        row.get("osm_id"),

                    "display_name":
                        row.get("display_name"),

                    "latitude":
                        float(row["lat"]),

                    "longitude":
                        float(row["lon"]),

                    "category":
                        row.get("category"),

                    "type":
                        row.get("type"),

                    "importance":
                        row.get("importance"),

                    "address":
                        row.get("address")
                        or {},
                }
            )

        resolved.append(
            {
                **candidate,

                "resolution_status":
                    (
                        "matches_found"
                        if matches
                        else
                        "not_found"
                    ),

                "resolution_query":
                    query,

                "matches":
                    matches,
            }
        )

        print(
            "  MATCHES =",
            len(matches),
        )

        time.sleep(1.1)

    OUTPUT.write_text(
        json.dumps(
            resolved,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "SAVED:",
        OUTPUT,
    )


if __name__ == "__main__":
    main()
