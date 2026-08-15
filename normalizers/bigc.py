from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "bigc.json"
)

NORMALIZED_FILE = (
    PROJECT_ROOT
    / "data"
    / "normalized"
    / "promotions.json"
)

FRONTEND_FILE = (
    PROJECT_ROOT
    / "promotions.json"
)


def load_raw() -> list[dict]:

    with RAW_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            "data/raw/bigc.json "
            "must contain a JSON list"
        )

    return data


def normalize_record(
    raw: dict,
) -> dict:

    title = (
        raw.get("title")
        or ""
    ).strip()

    source_url = (
        raw.get("destination_url")
        or ""
    ).strip()

    image_url = (
        raw.get("image_url")
        or ""
    ).strip()

    source_id = (
        raw.get("source_id")
        or ""
    ).strip()

    collected_at = (
        raw.get("collected_at")
        or ""
    ).strip()

    return {

        # =============================================
        # Canonical PrachinLife fields
        # =============================================

        "id":
            source_id,

        "promotion_type":
            "campaign",

        "title":
            title,

        "merchant":
            "Big C",

        "image_url":
            image_url,

        "source_url":
            source_url,

        "source":
            "Big C Official",

        "source_type":
            "official_promotion",

        "location_scope":
            "national",

        "province":
            None,

        "branch_name":
            None,

        "verified":
            True,

        "collected_at":
            collected_at,


        # =============================================
        # Legacy compatibility fields
        # Current app.js still reads these.
        # =============================================

        "store":
            "Big C",

        "product":
            title,

        "old_price":
            0,

        "new_price":
            0,

        "expiry":
            "ตรวจสอบรายละเอียดจาก Big C",

        "branch":
            (
                "Big C / "
                "ตรวจสอบสาขาที่ร่วมรายการ"
            ),

        "category":
            "แคมเปญโปรโมชั่น",

        "urgent":
            False,

        "image":
            image_url,
    }


def validate_normalized(
    records: list[dict],
) -> None:

    seen_ids: set[str] = set()

    for index, item in enumerate(
        records,
        start=1,
    ):

        required = {
            "id",
            "promotion_type",
            "title",
            "merchant",
            "source_url",
            "source",
            "verified",
            "collected_at",
        }

        missing = [
            field
            for field in required
            if not item.get(field)
        ]

        if missing:
            raise ValueError(
                f"record {index}: "
                f"missing values {missing}"
            )

        item_id = item["id"]

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: "
                f"duplicate id {item_id}"
            )

        seen_ids.add(
            item_id
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

    print(
        "=" * 60
    )

    print(
        "PrachinLife - Big C Normalizer V1"
    )

    print(
        "=" * 60
    )

    raw_records = load_raw()

    normalized = [
        normalize_record(
            item
        )
        for item in raw_records
    ]

    validate_normalized(
        normalized
    )

    save_json(
        NORMALIZED_FILE,
        normalized,
    )

    save_json(
        FRONTEND_FILE,
        normalized,
    )

    print(
        f"Raw records = "
        f"{len(raw_records)}"
    )

    print(
        f"Normalized records = "
        f"{len(normalized)}"
    )

    print(
        "Saved normalized:",
        NORMALIZED_FILE,
    )

    print(
        "Saved frontend compatibility:",
        FRONTEND_FILE,
    )

    print()
    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
