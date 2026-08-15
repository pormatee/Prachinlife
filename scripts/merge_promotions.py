from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

NORMALIZED_DIR = (
    PROJECT_ROOT
    / "data"
    / "normalized"
)

OUTPUT_FILE = (
    NORMALIZED_DIR
    / "promotions.json"
)

FRONTEND_FILE = (
    PROJECT_ROOT
    / "promotions.json"
)


SOURCE_FILES = [
    NORMALIZED_DIR / "bigc.json",
    NORMALIZED_DIR / "lotus.json",
]


def load_source(
    path: Path,
) -> list[dict]:

    if not path.exists():
        raise FileNotFoundError(
            f"Missing normalized source: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"{path} must contain a JSON list"
        )

    return data


def validate_merged(
    records: list[dict],
) -> None:

    seen_ids: set[str] = set()

    for index, item in enumerate(
        records,
        start=1,
    ):

        item_id = item.get("id")

        if not item_id:
            raise ValueError(
                f"record {index}: missing id"
            )

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: duplicate id {item_id}"
            )

        seen_ids.add(
            item_id
        )

        if not item.get("merchant"):
            raise ValueError(
                f"record {index}: missing merchant"
            )

        if not item.get("title"):
            raise ValueError(
                f"record {index}: missing title"
            )

        if not item.get("source"):
            raise ValueError(
                f"record {index}: missing source"
            )

        if not item.get("source_url"):
            raise ValueError(
                f"record {index}: missing source_url"
            )

        if item.get("verified") is not True:
            raise ValueError(
                f"record {index}: verified must be True"
            )


def save_json(
    path: Path,
    data: list[dict],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:

    print("=" * 60)
    print(
        "PrachinLife - Multi-source Merge Engine V1"
    )
    print("=" * 60)

    merged: list[dict] = []

    merchant_counts: dict[str, int] = {}

    for source_file in SOURCE_FILES:

        records = load_source(
            source_file
        )

        print(
            f"Loaded {source_file.name}: "
            f"{len(records)} records"
        )

        merged.extend(
            records
        )

    validate_merged(
        merged
    )

    merged.sort(
        key=lambda item:
            item.get("collected_at")
            or "",
        reverse=True,
    )

    for item in merged:

        merchant = (
            item.get("merchant")
            or "Unknown"
        )

        merchant_counts[merchant] = (
            merchant_counts.get(
                merchant,
                0,
            )
            + 1
        )

    save_json(
        OUTPUT_FILE,
        merged,
    )

    save_json(
        FRONTEND_FILE,
        merged,
    )

    print()
    print(
        f"Total merged records = "
        f"{len(merged)}"
    )

    print(
        "Merchant counts =",
        merchant_counts,
    )

    print(
        "Saved normalized:",
        OUTPUT_FILE,
    )

    print(
        "Saved frontend:",
        FRONTEND_FILE,
    )

    print()
    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
