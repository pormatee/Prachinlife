from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "lotus.json"
)

NORMALIZED_FILE = (
    PROJECT_ROOT
    / "data"
    / "normalized"
    / "lotus.json"
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
            "data/raw/lotus.json must contain a JSON list"
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

    source_id = (
        raw.get("source_id")
        or ""
    ).strip()

    collected_at = (
        raw.get("collected_at")
        or ""
    ).strip()

    raw_type = (
        raw.get("raw_type")
        or "campaign"
    ).strip()

    source_page = (
        raw.get("source_page")
        or "https://my.lotuss.com/promotions/th"
    ).strip()

    if raw_type not in ALLOWED_PROMOTION_TYPES:
        raw_type = "campaign"

    if raw_type == "coupon":
        category = "คูปอง"
    elif raw_type == "member_offer":
        category = "สิทธิสมาชิก"
    else:
        category = "แคมเปญโปรโมชั่น"

    return {
        "id": source_id,
        "promotion_type": raw_type,
        "title": title,
        "merchant": "Lotus's",

        "image_url": image_url,

        # Lotus card ไม่มี detail URL ที่ยืนยันได้ใน HTML
        # จึงใช้ source page เป็น provenance link
        "source_url": source_page,

        "source": "My Lotus's Official",
        "source_type": "official_promotion",
        "verified": True,
        "collected_at": collected_at,

        # Location Schema V1
        "location_scope": "national",
        "country": "TH",
        "province": None,
        "district": None,
        "subdistrict": None,
        "branch_name": None,

        # Frontend compatibility
        "store": "Lotus's",
        "product": title,
        "old_price": 0,
        "new_price": 0,
        "expiry": "ตรวจสอบรายละเอียดจาก Lotus's",
        "branch": "Lotus's / ตรวจสอบสาขาที่ร่วมรายการ",
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
            "image_url",
            "source_url",
            "source",
            "verified",
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
                f"record {index}: missing values {missing}"
            )

        if (
            item["promotion_type"]
            not in ALLOWED_PROMOTION_TYPES
        ):
            raise ValueError(
                f"record {index}: invalid promotion_type "
                f"{item['promotion_type']!r}"
            )

        item_id = item["id"]

        if item_id in seen_ids:
            raise ValueError(
                f"record {index}: duplicate id {item_id}"
            )

        seen_ids.add(item_id)

        if item.get("location_scope") != "national":
            raise ValueError(
                f"record {index}: Lotus V1 "
                f"must use national location_scope"
            )

        if item.get("country") != "TH":
            raise ValueError(
                f"record {index}: country must be 'TH'"
            )

        local_fields = {
            "province": item.get("province"),
            "district": item.get("district"),
            "subdistrict": item.get("subdistrict"),
            "branch_name": item.get("branch_name"),
        }

        populated = [
            field
            for field, value
            in local_fields.items()
            if value
        ]

        if populated:
            raise ValueError(
                f"record {index}: national record must not "
                f"contain local fields {populated}"
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
        "PrachinLife - Lotus's Normalizer V1"
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

    counts = {}

    for item in normalized:
        promotion_type = item["promotion_type"]

        counts[promotion_type] = (
            counts.get(
                promotion_type,
                0,
            )
            + 1
        )

    print(
        f"Raw records = {len(raw_records)}"
    )

    print(
        f"Normalized records = {len(normalized)}"
    )

    print(
        "Promotion types =",
        counts,
    )

    print(
        "Saved:",
        NORMALIZED_FILE,
    )

    print()
    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
