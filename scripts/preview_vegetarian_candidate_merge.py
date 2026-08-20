from __future__ import annotations

import json
from pathlib import Path


PRODUCTION_FILE = Path(
    "vegetarian_index.json"
)

CANDIDATE_FILE = Path(
    "data/candidates/vegetarian_candidates.json"
)


def load_json(path):
    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, list):
        raise SystemExit(
            f"ERROR: {path} must contain an array"
        )

    return data


def normalize_title(value):
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def candidate_key(item):
    location = item.get("location") or {}

    return (
        normalize_title(
            item.get("title")
        ),
        normalize_title(
            location.get("province")
        ),
    )


def main():
    production = load_json(
        PRODUCTION_FILE
    )

    candidates = load_json(
        CANDIDATE_FILE
    )

    existing_ids = {
        item.get("id")
        for item in production
        if item.get("id")
    }

    existing_keys = {
        candidate_key(item)
        for item in production
    }

    new_records = []
    duplicate_records = []

    for item in candidates:

        item_id = item.get("id")
        key = candidate_key(item)

        if (
            item_id
            and item_id in existing_ids
        ):
            duplicate_records.append(
                (
                    item,
                    "duplicate_id",
                )
            )
            continue

        if key in existing_keys:
            duplicate_records.append(
                (
                    item,
                    "duplicate_title_province",
                )
            )
            continue

        new_records.append(item)

    print("=" * 60)
    print("VEGETARIAN MERGE PREVIEW")
    print("=" * 60)

    print(
        "PRODUCTION =",
        len(production),
    )

    print(
        "CANDIDATES =",
        len(candidates),
    )

    print(
        "NEW =",
        len(new_records),
    )

    print(
        "DUPLICATES =",
        len(duplicate_records),
    )

    if new_records:
        print()
        print("NEW RECORDS")

        for item in new_records:
            print(
                "-",
                item.get("title"),
                "|",
                (
                    item.get("location")
                    or {}
                ).get("province"),
                "|",
                (
                    item.get("metadata")
                    or {}
                ).get("display_tier"),
            )

    if duplicate_records:
        print()
        print("DUPLICATES")

        for item, reason in duplicate_records:
            print(
                "-",
                item.get("title"),
                "|",
                reason,
            )

    print()
    print(
        "PREVIEW ONLY - production not modified"
    )


if __name__ == "__main__":
    main()
