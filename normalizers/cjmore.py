from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cjmore.json"
)

NORMALIZED_FILE = (
    PROJECT_ROOT
    / "data"
    / "normalized"
    / "cjmore.json"
)

ALLOWED_PROMOTION_TYPES = {
    "campaign",
    "member_offer",
    "coupon",
}


def load_raw() -> list[dict]:
    with RAW_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "data/raw/cjmore.json "
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

    image_url = (
        raw.get("image_url")
        or ""
    ).strip()

    source_url = (
        raw.get("destination_url")
        or raw.get("source_page")
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

    promotion_type = (
        raw.get("raw_type")
        or "campaign"
    ).strip()

    if (
        promotion_type
        not in ALLOWED_PROMOTION_TYPES
    ):
        promotion_type = "campaign"

    category = {
        "coupon": "คูปอง",
        "member_offer": "สิทธิสมาชิก",
        "campaign": "แคมเปญโปรโมชั่น",
    }[promotion_type]

    return {
        "id": source_id,
        "promotion_type": promotion_type,
        "title": title,
        "merchant": "CJ MORE",
        "image_url": image_url,
        "source_url": source_url,
        "source": "CJ MORE Official",
        "source_type": "official_promotion",
        "verified": True,
        "collected_at": collected_at,

        "location_scope": "national",
        "country": "TH",
        "province": None,
        "district": None,
        "subdistrict": None,
        "branch_name": None,

        "store": "CJ MORE",
        "product": title,
        "old_price": 0,
        "new_price": 0,
        "expiry": (
            "ตรวจสอบรายละเอียดจาก CJ MORE"
        ),
        "branch": (
            "CJ MORE / "
            "ตรวจสอบสาขาที่ร่วมรายการ"
        ),
        "category": category,
        "urgent": False,
        "image": image_url,
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
            "collected_at",
            "location_scope",
            "country",
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

        if item.get("verified") is not True:
            raise ValueError(
                f"record {index}: "
                "verified must be True"
            )

        item_id = item["id"]

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: "
                f"duplicate id {item_id}"
            )

        seen_ids.add(item_id)

        if (
            item["promotion_type"]
            not in ALLOWED_PROMOTION_TYPES
        ):
            raise ValueError(
                f"record {index}: "
                "invalid promotion_type"
            )

        if (
            item.get("location_scope")
            != "national"
        ):
            raise ValueError(
                f"record {index}: "
                "CJ MORE must use "
                "national location_scope"
            )

        if item.get("country") != "TH":
            raise ValueError(
                f"record {index}: "
                "country must be TH"
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
        "PrachinLife - "
        "CJ MORE Normalizer V1"
    )
    print("=" * 60)

    raw_records = load_raw()

    normalized = [
        normalize_record(item)
        for item in raw_records
    ]

    validate_normalized(
        normalized
    )

    save_json(
        NORMALIZED_FILE,
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
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
