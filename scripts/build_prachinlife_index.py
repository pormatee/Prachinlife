from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

NORMALIZED_DIR = (
    PROJECT_ROOT
    / "data"
    / "normalized"
)

PROMOTIONS_FILE = (
    NORMALIZED_DIR
    / "promotions.json"
)

OUTPUT_FILE = (
    NORMALIZED_DIR
    / "prachinlife_index.json"
)

FRONTEND_FILE = (
    PROJECT_ROOT
    / "prachinlife_index.json"
)


SCHEMA_VERSION = "1.0"


def load_json_list(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        raise FileNotFoundError(
            f"Missing source file: {path}"
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

    records: list[dict[str, Any]] = []

    for index, item in enumerate(
        data,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                f"{path.name} record {index} "
                "must be an object"
            )

        records.append(item)

    return records


def clean_text(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def normalize_tag(
    value: Any,
) -> str | None:

    text = clean_text(value)

    if not text:
        return None

    return (
        text
        .lower()
        .replace("'", "")
        .replace("’", "")
        .strip()
    )


def build_tags(
    promotion: dict[str, Any],
) -> list[str]:

    tags: list[str] = []

    def add(value: Any) -> None:

        normalized = normalize_tag(
            value
        )

        if (
            normalized
            and normalized not in tags
        ):
            tags.append(
                normalized
            )

    add("deal")

    merchant = promotion.get(
        "merchant"
    )

    promotion_type = promotion.get(
        "promotion_type"
    )

    category = promotion.get(
        "category"
    )

    add(merchant)
    add(promotion_type)
    add(category)

    if (
        promotion_type
        == "coupon"
    ):
        add("saving")
        add("coupon")

    elif (
        promotion_type
        == "member_offer"
    ):
        add("benefit")
        add("membership")

    elif (
        promotion_type
        == "product_deal"
    ):
        add("saving")
        add("product")

    else:
        add("campaign")

    location_scope = promotion.get(
        "location_scope"
    )

    add(location_scope)

    add(
        promotion.get(
            "province"
        )
    )

    add(
        promotion.get(
            "district"
        )
    )

    add(
        promotion.get(
            "subdistrict"
        )
    )

    add(
        promotion.get(
            "branch_name"
        )
    )

    return tags


def build_summary(
    promotion: dict[str, Any],
) -> str:

    promotion_type = (
        promotion.get(
            "promotion_type"
        )
        or "campaign"
    )

    merchant = (
        promotion.get(
            "merchant"
        )
        or "แหล่งต้นทาง"
    )

    if promotion_type == "coupon":
        return (
            f"คูปองหรือสิทธิ์ส่วนลดจาก "
            f"{merchant}"
        )

    if (
        promotion_type
        == "member_offer"
    ):
        return (
            f"สิทธิประโยชน์สำหรับสมาชิกจาก "
            f"{merchant}"
        )

    if (
        promotion_type
        == "product_deal"
    ):
        return (
            f"ดีลสินค้าจาก "
            f"{merchant}"
        )

    return (
        f"แคมเปญหรือโปรโมชั่นจาก "
        f"{merchant}"
    )


def map_category(
    promotion: dict[str, Any],
) -> str:

    promotion_type = (
        promotion.get(
            "promotion_type"
        )
        or "campaign"
    )

    if promotion_type == "coupon":
        return "shopping"

    if (
        promotion_type
        == "member_offer"
    ):
        return "shopping"

    if (
        promotion_type
        == "product_deal"
    ):
        return "shopping"

    return "shopping"


def build_location(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "scope": (
            promotion.get(
                "location_scope"
            )
            or "national"
        ),
        "country": (
            promotion.get(
                "country"
            )
            or "TH"
        ),
        "province": promotion.get(
            "province"
        ),
        "district": promotion.get(
            "district"
        ),
        "subdistrict": promotion.get(
            "subdistrict"
        ),
        "place_name": (
            promotion.get(
                "branch_name"
            )
            or None
        ),
    }


def build_source(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "name": (
            promotion.get(
                "source"
            )
            or promotion.get(
                "merchant"
            )
            or "Unknown"
        ),
        "url": (
            promotion.get(
                "source_url"
            )
            or None
        ),
        "type": (
            promotion.get(
                "source_type"
            )
            or "unknown"
        ),
        "verified": (
            promotion.get(
                "verified"
            )
            is True
        ),
    }


def build_provider(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "name": (
            promotion.get(
                "merchant"
            )
            or promotion.get(
                "store"
            )
            or "Unknown"
        ),
        "type": "merchant",
    }


def map_promotion(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    item_id = clean_text(
        promotion.get(
            "id"
        )
    )

    title = clean_text(
        promotion.get(
            "title"
        )
        or promotion.get(
            "product"
        )
    )

    if not item_id:
        raise ValueError(
            "Promotion missing id"
        )

    if not title:
        raise ValueError(
            f"{item_id}: missing title"
        )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "id": item_id,

        "content_type":
            "deal",

        "original_type": (
            promotion.get(
                "promotion_type"
            )
            or "campaign"
        ),

        "title": title,

        "summary":
            build_summary(
                promotion
            ),

        "category":
            map_category(
                promotion
            ),

        "tags":
            build_tags(
                promotion
            ),

        "provider":
            build_provider(
                promotion
            ),

        "location":
            build_location(
                promotion
            ),

        "source":
            build_source(
                promotion
            ),

        "image_url": (
            promotion.get(
                "image_url"
            )
            or promotion.get(
                "image"
            )
            or None
        ),

        "published_at":
            promotion.get(
                "published_at"
            ),

        "expires_at":
            promotion.get(
                "expires_at"
            ),

        "collected_at":
            promotion.get(
                "collected_at"
            ),

        "metadata": {
            "old_price":
                promotion.get(
                    "old_price"
                ),

            "new_price":
                promotion.get(
                    "new_price"
                ),

            "expiry_text":
                promotion.get(
                    "expiry"
                ),

            "urgent":
                promotion.get(
                    "urgent"
                )
                is True,
        },
    }


def validate_index(
    records: list[
        dict[str, Any]
    ],
) -> None:

    seen_ids: set[str] = set()

    allowed_content_types = {
        "deal",
        "place",
        "service",
        "event",
        "information",
    }

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
                f"record {index}: "
                f"duplicate id {item_id}"
            )

        seen_ids.add(
            item_id
        )

        content_type = item.get(
            "content_type"
        )

        if (
            content_type
            not in allowed_content_types
        ):
            raise ValueError(
                f"{item_id}: invalid "
                f"content_type "
                f"{content_type}"
            )

        if not item.get("title"):
            raise ValueError(
                f"{item_id}: missing title"
            )

        source = item.get(
            "source"
        )

        if not isinstance(
            source,
            dict,
        ):
            raise ValueError(
                f"{item_id}: invalid source"
            )

        if source.get(
            "verified"
        ) is not True:
            raise ValueError(
                f"{item_id}: "
                "source must be verified"
            )

        location = item.get(
            "location"
        )

        if not isinstance(
            location,
            dict,
        ):
            raise ValueError(
                f"{item_id}: "
                "invalid location"
            )

        tags = item.get(
            "tags"
        )

        if not isinstance(
            tags,
            list,
        ):
            raise ValueError(
                f"{item_id}: tags must "
                "be a list"
            )


def save_json(
    path: Path,
    data: list[
        dict[str, Any]
    ],
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
        "Common Content Index V1"
    )

    print("=" * 60)

    promotions = load_json_list(
        PROMOTIONS_FILE
    )

    print(
        "Loaded promotions:",
        len(promotions),
    )

    index_records = [
        map_promotion(
            promotion
        )
        for promotion
        in promotions
    ]

    index_records.sort(
        key=lambda item:
            item.get(
                "collected_at"
            )
            or "",
        reverse=True,
    )

    validate_index(
        index_records
    )

    save_json(
        OUTPUT_FILE,
        index_records,
    )

    save_json(
        FRONTEND_FILE,
        index_records,
    )

    content_counts: dict[
        str,
        int,
    ] = {}

    for item in index_records:

        content_type = (
            item.get(
                "content_type"
            )
            or "unknown"
        )

        content_counts[
            content_type
        ] = (
            content_counts.get(
                content_type,
                0,
            )
            + 1
        )

    print()

    print(
        "Total index records =",
        len(index_records),
    )

    print(
        "Content counts =",
        content_counts,
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
