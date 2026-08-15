from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "promotions.json"


REQUIRED_FIELDS = {
    "id",
    "promotion_type",
    "title",
    "merchant",
    "source_url",
    "source",
    "verified",
    "collected_at",
}


def load_data() -> list[dict]:
    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "promotions.json must contain a JSON list"
        )

    return data


def validate_record(
    item: dict,
    index: int,
) -> list[str]:

    errors: list[str] = []

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in item
    ]

    if missing:
        errors.append(
            f"record {index}: missing fields {missing}"
        )

    if not item.get("id"):
        errors.append(
            f"record {index}: id is empty"
        )

    if not item.get("title"):
        errors.append(
            f"record {index}: title is empty"
        )

    if not item.get("merchant"):
        errors.append(
            f"record {index}: merchant is empty"
        )

    if item.get("promotion_type") not in {
        "campaign",
        "product_deal",
    }:
        errors.append(
            f"record {index}: invalid promotion_type "
            f"{item.get('promotion_type')!r}"
        )

    if not item.get("source_url"):
        errors.append(
            f"record {index}: source_url is empty"
        )

    if item.get("verified") is not True:
        errors.append(
            f"record {index}: verified must be True"
        )

    return errors


def main() -> None:

    print("=" * 60)
    print("PrachinLife Data Validator V1")
    print("=" * 60)

    data = load_data()

    errors: list[str] = []

    ids: set[str] = set()

    for index, item in enumerate(
        data,
        start=1,
    ):

        errors.extend(
            validate_record(
                item,
                index,
            )
        )

        item_id = item.get("id")

        if item_id:

            if item_id in ids:
                errors.append(
                    f"record {index}: duplicate id {item_id}"
                )

            ids.add(item_id)

    print(
        f"Records = {len(data)}"
    )

    print(
        f"Unique IDs = {len(ids)}"
    )

    print(
        f"Errors = {len(errors)}"
    )

    if errors:

        print()

        for error in errors:
            print(
                "[FAIL]",
                error,
            )

        raise SystemExit(1)

    print()
    print("FINAL RESULT: PASS")


if __name__ == "__main__":
    main()
