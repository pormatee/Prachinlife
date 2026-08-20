from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_CANDIDATE_FILE = Path(
    "data/candidates/vegetarian_candidates.json"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate PrachinLife vegetarian candidates"
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_CANDIDATE_FILE),
    )

    return parser.parse_args()


ALLOWED_TIERS = {
    "dedicated",
    "named_candidate",
    "option_available",
}


def load_candidates(path):
    if not path.exists():
        raise SystemExit(
            f"ERROR: file not found: {path}"
        )

    data = json.loads(
        path.read_text(
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
    source_ref = item.get("source_ref")

    has_valid_url = (
        isinstance(source_url, str)
        and source_url.startswith(
            ("http://", "https://")
        )
    )

    has_source_ref = (
        isinstance(source_ref, str)
        and bool(source_ref.strip())
    )

    if not (
        has_valid_url
        or has_source_ref
    ):
        errors.append(
            f"#{index}: missing source evidence"
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
    args = parse_args()

    candidate_file = Path(
        args.input
    )

    candidates = load_candidates(
        candidate_file
    )

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

    print("INPUT =", candidate_file)
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
