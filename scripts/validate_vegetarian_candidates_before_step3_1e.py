from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


CANDIDATE_FILE = Path(
    "data/candidates/vegetarian_candidates.json"
)


ALLOWED_TIERS = {
    "dedicated",
    "named_candidate",
    "option_available",
}


def load_candidates():
    if not CANDIDATE_FILE.exists():
        raise SystemExit(
            f"ERROR: file not found: {CANDIDATE_FILE}"
        )

    data = json.loads(
        CANDIDATE_FILE.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, list):
        raise SystemExit(
            "ERROR: candidate file must be a JSON array"
        )

    return data


def validate_candidate(item, index):
    errors = []

    if not isinstance(item, dict):
        return [
            f"#{index}: record must be an object"
        ]

    title = item.get("title")
    location = item.get("location") or {}
    metadata = item.get("metadata") or {}

    if not isinstance(title, str) or not title.strip():
        errors.append(
            f"#{index}: missing title"
        )

    province = location.get("province")

    if (
        not isinstance(province, str)
        or not province.strip()
    ):
        errors.append(
            f"#{index}: missing province"
        )

    source_url = item.get("source_url")

    if (
        not isinstance(source_url, str)
        or not source_url.startswith(
            ("http://", "https://")
        )
    ):
        errors.append(
            f"#{index}: invalid source_url"
        )

    tier = metadata.get("display_tier")

    if tier not in ALLOWED_TIERS:
        errors.append(
            f"#{index}: invalid display_tier={tier!r}"
        )

    latitude = location.get("latitude")
    longitude = location.get("longitude")

    has_lat = isinstance(
        latitude,
        (int, float),
    )

    has_lon = isinstance(
        longitude,
        (int, float),
    )

    if has_lat != has_lon:
        errors.append(
            f"#{index}: latitude/longitude incomplete"
        )

    if has_lat and not (-90 <= latitude <= 90):
        errors.append(
            f"#{index}: invalid latitude"
        )

    if has_lon and not (-180 <= longitude <= 180):
        errors.append(
            f"#{index}: invalid longitude"
        )

    evidence = metadata.get(
        "evidence_reason"
    )

    if (
        not isinstance(evidence, str)
        or not evidence.strip()
    ):
        errors.append(
            f"#{index}: missing evidence_reason"
        )

    return errors


def main():
    candidates = load_candidates()

    all_errors = []

    for index, item in enumerate(
        candidates,
        start=1,
    ):
        all_errors.extend(
            validate_candidate(
                item,
                index,
            )
        )

    print("=" * 60)
    print("VEGETARIAN CANDIDATE VALIDATION")
    print("=" * 60)

    print("TOTAL =", len(candidates))

    tiers = Counter(
        (
            item.get("metadata") or {}
        ).get("display_tier")
        for item in candidates
        if isinstance(item, dict)
    )

    provinces = Counter(
        (
            item.get("location") or {}
        ).get("province")
        for item in candidates
        if isinstance(item, dict)
    )

    print("TIERS =", dict(tiers))
    print(
        "PROVINCES =",
        dict(provinces),
    )

    if all_errors:
        print()
        print("ERRORS")

        for error in all_errors:
            print("-", error)

        print()
        print("FINAL RESULT: FAIL")

        raise SystemExit(1)

    print()
    print("FINAL RESULT: PASS")


if __name__ == "__main__":
    main()
