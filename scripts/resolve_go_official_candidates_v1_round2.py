from __future__ import annotations

import json
import time
from pathlib import Path

import requests


INPUT = Path(
    "data/candidates/"
    "go_official_candidates_qualified_v1.json"
)

OUTPUT = Path(
    "data/candidates/"
    "go_official_candidates_resolved_v1_round2.json"
)

USER_AGENT = (
    "PrachinLife-GoDiscoveryV1-Round2/1.0"
)

ALIASES = {
    "พิพิธภัณฑสถานแห่งชาติปราจีนบุรี": [
        "Prachinburi National Museum",
    ],
    "เมืองโบราณศรีมโหสถ": [
        "Si Mahosot Ancient Town",
        "ศรีมโหสถ",
    ],
    "โบราณสถานสระมรกต": [
        "Sa Morakot Archaeological Site",
        "สระมรกต ศรีมโหสถ",
    ],
    "ต้นโพธิ์ศรีมหาโพธิ": [
        "ต้นศรีมหาโพธิ ศรีมโหสถ",
        "Sri Maha Bodhi Tree Prachinburi",
    ],
    "แก่งหินเพิง": [
        "Kaeng Hin Phoeng",
    ],
    "น้ำตกเขาอีโต้": [
        "Khao Ito Waterfall",
    ],
    "น้ำตกธารรัตนา": [
        "Than Rattana Waterfall",
    ],
    "พิพิธภัณฑ์อยู่สุขสุวรรณ์": [
        "Yusuksuwan Museum",
    ],
    "อุทยานแห่งชาติทับลาน": [
        "Thap Lan National Park",
    ],
}


def queries_for(title):
    names = [title] + ALIASES.get(title, [])

    queries = []

    for name in names:
        queries.extend([
            f"{name}, จังหวัดปราจีนบุรี, ประเทศไทย",
            f"{name}, Prachin Buri, Thailand",
            f"{name}, Thailand",
        ])

    return list(dict.fromkeys(queries))


def search(query):
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

    return response.json()


def main():
    rows = json.loads(
        INPUT.read_text(
            encoding="utf-8"
        )
    )

    targets = [
        x for x in rows
        if x.get(
            "qualification_status"
        ) != "auto_match"
    ]

    output = []

    for i, row in enumerate(
        targets,
        1,
    ):
        title = row["title"]

        print(
            f"[{i}/{len(targets)}] "
            f"{title}"
        )

        found = []

        for query in queries_for(title):
            try:
                matches = search(query)

            except Exception as error:
                print(
                    "  ERROR:",
                    error,
                )
                time.sleep(1.1)
                continue

            for match in matches:
                found.append({
                    "query": query,
                    "osm_type":
                        match.get("osm_type"),
                    "osm_id":
                        match.get("osm_id"),
                    "display_name":
                        match.get("display_name"),
                    "latitude":
                        float(match["lat"]),
                    "longitude":
                        float(match["lon"]),
                    "category":
                        match.get("category"),
                    "type":
                        match.get("type"),
                    "importance":
                        match.get("importance"),
                    "address":
                        match.get("address")
                        or {},
                })

            if matches:
                break

            time.sleep(1.1)

        output.append({
            "title": title,
            "previous_status":
                row.get(
                    "qualification_status"
                ),
            "matches": found,
        })

        print(
            "  MATCHES =",
            len(found),
        )

        time.sleep(1.1)

    OUTPUT.write_text(
        json.dumps(
            output,
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
