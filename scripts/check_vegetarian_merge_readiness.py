from __future__ import annotations

import json
from pathlib import Path


CANDIDATE_FILE = Path(
    "data/candidates/vegetarian_candidates.json"
)


def main():
    data = json.loads(
        CANDIDATE_FILE.read_text(
            encoding="utf-8"
        )
    )

    ready = []
    blocked = []

    for item in data:

        metadata = item.get("metadata") or {}
        location = item.get("location") or {}

        reasons = []

        if (
            metadata.get("display_tier")
            != "dedicated"
        ):
            reasons.append(
                "not_dedicated"
            )

        if (
            metadata.get("needs_review")
            is True
        ):
            reasons.append(
                "needs_review"
            )

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if not isinstance(
            latitude,
            (int, float),
        ):
            reasons.append(
                "missing_latitude"
            )

        if not isinstance(
            longitude,
            (int, float),
        ):
            reasons.append(
                "missing_longitude"
            )

        if reasons:
            blocked.append(
                (
                    item,
                    reasons,
                )
            )
        else:
            ready.append(item)

    print("=" * 60)
    print("VEGETARIAN MERGE READINESS")
    print("=" * 60)

    print(
        "CANDIDATES =",
        len(data),
    )

    print(
        "READY =",
        len(ready),
    )

    print(
        "BLOCKED =",
        len(blocked),
    )

    if ready:
        print()
        print("READY FOR PRODUCTION")

        for item in ready:
            print(
                "-",
                item.get("title"),
            )

    if blocked:
        print()
        print("BLOCKED")

        for item, reasons in blocked:
            print(
                "-",
                item.get("title"),
                "|",
                ", ".join(reasons),
            )

    print()
    print(
        "PRODUCTION NOT MODIFIED"
    )


if __name__ == "__main__":
    main()
