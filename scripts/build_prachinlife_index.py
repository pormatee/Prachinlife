from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# CONFIG
# ============================================================

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

RESTAURANTS_FILE = (
    NORMALIZED_DIR
    / "restaurants.json"
)

OUTPUT_FILE = (
    NORMALIZED_DIR
    / "prachinlife_index.json"
)

FRONTEND_FILE = (
    PROJECT_ROOT
    / "prachinlife_index.json"
)


SCHEMA_VERSION = "1.1"


# ============================================================
# LOAD
# ============================================================

def load_json_list(
    path: Path,
    required: bool = True,
) -> list[dict[str, Any]]:

    if not path.exists():

        if required:
            raise FileNotFoundError(
                f"Missing source file: {path}"
            )

        print(
            f"Optional source not found: {path.name}"
        )

        return []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            f"{path} must contain a JSON list"
        )

    records: list[
        dict[str, Any]
    ] = []

    for index, item in enumerate(
        data,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                f"{path.name} record "
                f"{index} must be an object"
            )

        records.append(
            item
        )

    return records


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text


def normalize_tag(
    value: Any,
) -> str | None:

    text = clean_text(
        value
    )

    if not text:
        return None

    return (
        text
        .lower()
        .replace(
            "'",
            "",
        )
        .replace(
            "’",
            "",
        )
        .strip()
    )


def add_tag(
    tags: list[str],
    value: Any,
) -> None:

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


# ============================================================
# DEAL TAGS
# ============================================================

def build_deal_tags(
    promotion: dict[str, Any],
) -> list[str]:

    tags: list[str] = []

    add_tag(
        tags,
        "deal",
    )

    merchant = promotion.get(
        "merchant"
    )

    promotion_type = promotion.get(
        "promotion_type"
    )

    category = promotion.get(
        "category"
    )

    add_tag(
        tags,
        merchant,
    )

    add_tag(
        tags,
        promotion_type,
    )

    add_tag(
        tags,
        category,
    )

    merchant_text = (
        clean_text(
            merchant
        )
        or ""
    ).lower()

    if "lotus" in merchant_text:

        add_tag(
            tags,
            "lotus",
        )

        add_tag(
            tags,
            "โลตัส",
        )

    if "big c" in merchant_text:

        add_tag(
            tags,
            "bigc",
        )

        add_tag(
            tags,
            "บิ๊กซี",
        )

    if (
        "cj more" in merchant_text
        or "cjmore" in merchant_text
    ):

        add_tag(
            tags,
            "cjmore",
        )

        add_tag(
            tags,
            "ซีเจ",
        )

        add_tag(
            tags,
            "ซีเจ มอร์",
        )

    if (
        promotion_type
        == "coupon"
    ):

        add_tag(
            tags,
            "saving",
        )

        add_tag(
            tags,
            "coupon",
        )

        add_tag(
            tags,
            "คูปอง",
        )

    elif (
        promotion_type
        == "member_offer"
    ):

        add_tag(
            tags,
            "benefit",
        )

        add_tag(
            tags,
            "membership",
        )

        add_tag(
            tags,
            "สมาชิก",
        )

    elif (
        promotion_type
        == "product_deal"
    ):

        add_tag(
            tags,
            "saving",
        )

        add_tag(
            tags,
            "product",
        )

    else:

        add_tag(
            tags,
            "campaign",
        )

        add_tag(
            tags,
            "แคมเปญ",
        )

    add_tag(
        tags,
        promotion.get(
            "location_scope"
        ),
    )

    add_tag(
        tags,
        promotion.get(
            "province"
        ),
    )

    add_tag(
        tags,
        promotion.get(
            "district"
        ),
    )

    add_tag(
        tags,
        promotion.get(
            "subdistrict"
        ),
    )

    add_tag(
        tags,
        promotion.get(
            "branch_name"
        ),
    )

    return tags


# ============================================================
# DEAL HELPERS
# ============================================================

def build_deal_summary(
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

    if (
        promotion_type
        == "coupon"
    ):

        return (
            "คูปองหรือสิทธิ์ส่วนลดจาก "
            f"{merchant}"
        )

    if (
        promotion_type
        == "member_offer"
    ):

        return (
            "สิทธิประโยชน์สำหรับสมาชิกจาก "
            f"{merchant}"
        )

    if (
        promotion_type
        == "product_deal"
    ):

        return (
            "ดีลสินค้าจาก "
            f"{merchant}"
        )

    return (
        "แคมเปญหรือโปรโมชั่นจาก "
        f"{merchant}"
    )


def build_deal_location(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "scope":
            (
                promotion.get(
                    "location_scope"
                )
                or "national"
            ),

        "country":
            (
                promotion.get(
                    "country"
                )
                or "TH"
            ),

        "province":
            promotion.get(
                "province"
            ),

        "district":
            promotion.get(
                "district"
            ),

        "subdistrict":
            promotion.get(
                "subdistrict"
            ),

        "place_name":
            (
                promotion.get(
                    "branch_name"
                )
                or None
            ),

        "latitude":
            None,

        "longitude":
            None,
    }


def build_deal_source(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "name":
            (
                promotion.get(
                    "source"
                )
                or promotion.get(
                    "merchant"
                )
                or "Unknown"
            ),

        "url":
            (
                promotion.get(
                    "source_url"
                )
                or None
            ),

        "type":
            (
                promotion.get(
                    "source_type"
                )
                or "unknown"
            ),

        "verified":
            (
                promotion.get(
                    "verified"
                )
                is True
            ),
    }


def build_deal_provider(
    promotion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "name":
            (
                promotion.get(
                    "merchant"
                )
                or promotion.get(
                    "store"
                )
                or "Unknown"
            ),

        "type":
            "merchant",
    }


# ============================================================
# MAP DEAL
# ============================================================

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

        "id":
            item_id,

        "content_type":
            "deal",

        "original_type":
            (
                promotion.get(
                    "promotion_type"
                )
                or "campaign"
            ),

        "title":
            title,

        "summary":
            build_deal_summary(
                promotion
            ),

        "category":
            "shopping",

        "tags":
            build_deal_tags(
                promotion
            ),

        "provider":
            build_deal_provider(
                promotion
            ),

        "location":
            build_deal_location(
                promotion
            ),

        "source":
            build_deal_source(
                promotion
            ),

        "image_url":
            (
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
                (
                    promotion.get(
                        "urgent"
                    )
                    is True
                ),
        },
    }


# ============================================================
# EAT TAGS
# ============================================================

def build_eat_tags(
    restaurant: dict[str, Any],
) -> list[str]:

    tags: list[str] = []

    add_tag(
        tags,
        "eat",
    )

    add_tag(
        tags,
        "อาหาร",
    )

    add_tag(
        tags,
        restaurant.get(
            "category"
        ),
    )

    add_tag(
        tags,
        restaurant.get(
            "category_label"
        ),
    )

    category = clean_text(
        restaurant.get(
            "category"
        )
    )

    if category == "cafe":

        add_tag(
            tags,
            "coffee",
        )

        add_tag(
            tags,
            "กาแฟ",
        )

        add_tag(
            tags,
            "คาเฟ่",
        )

    elif category == "restaurant":

        add_tag(
            tags,
            "restaurant",
        )

        add_tag(
            tags,
            "ร้านอาหาร",
        )

    elif category == "fast_food":

        add_tag(
            tags,
            "fast food",
        )

        add_tag(
            tags,
            "อาหารจานด่วน",
        )

    elif category == "food_court":

        add_tag(
            tags,
            "food court",
        )

        add_tag(
            tags,
            "ศูนย์อาหาร",
        )

    elif category == "ice_cream":

        add_tag(
            tags,
            "ice cream",
        )

        add_tag(
            tags,
            "ไอศกรีม",
        )

    cuisine = restaurant.get(
        "cuisine"
    )

    if isinstance(
        cuisine,
        list,
    ):

        for item in cuisine:

            add_tag(
                tags,
                item,
            )

    location = restaurant.get(
        "location"
    )

    if isinstance(
        location,
        dict,
    ):

        add_tag(
            tags,
            location.get(
                "province"
            ),
        )

        add_tag(
            tags,
            location.get(
                "district"
            ),
        )

        add_tag(
            tags,
            location.get(
                "subdistrict"
            ),
        )

    return tags


# ============================================================
# EAT SUMMARY
# ============================================================

def build_eat_summary(
    restaurant: dict[str, Any],
) -> str:

    category_label = (
        clean_text(
            restaurant.get(
                "category_label"
            )
        )
        or "ร้านอาหารและเครื่องดื่ม"
    )

    location = restaurant.get(
        "location"
    )

    district = None

    if isinstance(
        location,
        dict,
    ):

        district = clean_text(
            location.get(
                "district"
            )
        )

    if district:

        return (
            f"{category_label}ในพื้นที่"
            f"{district} จังหวัดปราจีนบุรี"
        )

    return (
        f"{category_label}"
        "ในจังหวัดปราจีนบุรี"
    )


# ============================================================
# EAT LOCATION
# ============================================================

def build_eat_location(
    restaurant: dict[str, Any],
) -> dict[str, Any]:

    source_location = restaurant.get(
        "location"
    )

    if not isinstance(
        source_location,
        dict,
    ):

        source_location = {}

    return {
        "scope":
            "place",

        "country":
            (
                source_location.get(
                    "country"
                )
                or "TH"
            ),

        "province":
            (
                source_location.get(
                    "province"
                )
                or "ปราจีนบุรี"
            ),

        "district":
            source_location.get(
                "district"
            ),

        "subdistrict":
            source_location.get(
                "subdistrict"
            ),

        "place_name":
            restaurant.get(
                "name"
            ),

        "street":
            source_location.get(
                "street"
            ),

        "house_number":
            source_location.get(
                "house_number"
            ),

        "postcode":
            source_location.get(
                "postcode"
            ),

        "latitude":
            source_location.get(
                "latitude"
            ),

        "longitude":
            source_location.get(
                "longitude"
            ),
    }


# ============================================================
# MAP EAT
# ============================================================

def map_restaurant(
    restaurant: dict[str, Any],
) -> dict[str, Any]:

    item_id = clean_text(
        restaurant.get(
            "id"
        )
    )

    name = clean_text(
        restaurant.get(
            "name"
        )
    )

    if not item_id:

        raise ValueError(
            "Eat record missing id"
        )

    if not name:

        raise ValueError(
            f"{item_id}: missing name"
        )

    source = restaurant.get(
        "source"
    )

    if not isinstance(
        source,
        dict,
    ):

        source = {}

    contact = restaurant.get(
        "contact"
    )

    if not isinstance(
        contact,
        dict,
    ):

        contact = {}

    features = restaurant.get(
        "features"
    )

    if not isinstance(
        features,
        dict,
    ):

        features = {}

    cuisine = restaurant.get(
        "cuisine"
    )

    if not isinstance(
        cuisine,
        list,
    ):

        cuisine = []

    return {
        "schema_version":
            SCHEMA_VERSION,

        "id":
            item_id,

        "content_type":
            "eat",

        "original_type":
            (
                restaurant.get(
                    "category"
                )
                or "restaurant"
            ),

        "title":
            name,

        "summary":
            build_eat_summary(
                restaurant
            ),

        "category":
            (
                restaurant.get(
                    "category"
                )
                or "restaurant"
            ),

        "tags":
            build_eat_tags(
                restaurant
            ),

        "provider": {
            "name":
                name,

            "type":
                "place",
        },

        "location":
            build_eat_location(
                restaurant
            ),

        "source": {
            "name":
                (
                    source.get(
                        "name"
                    )
                    or "OpenStreetMap"
                ),

            "url":
                source.get(
                    "url"
                ),

            "type":
                (
                    source.get(
                        "type"
                    )
                    or "open_data"
                ),

            "verified":
                (
                    source.get(
                        "verified"
                    )
                    is True
                ),
        },

        "image_url":
            restaurant.get(
                "image_url"
            ),

        "published_at":
            None,

        "expires_at":
            None,

        "collected_at":
            restaurant.get(
                "collected_at"
            ),

        "metadata": {
            "name_th":
                restaurant.get(
                    "name_th"
                ),

            "name_en":
                restaurant.get(
                    "name_en"
                ),

            "category_label":
                restaurant.get(
                    "category_label"
                ),

            "cuisine":
                cuisine,

            "opening_hours":
                restaurant.get(
                    "opening_hours"
                ),

            "contact":
                contact,

            "features":
                features,
        },
    }


# ============================================================
# VALIDATE COMMON INDEX
# ============================================================

def validate_index(
    records: list[
        dict[str, Any]
    ],
) -> None:

    seen_ids: set[str] = set()

    allowed_content_types = {
        "deal",
        "eat",
        "place",
        "service",
        "event",
        "information",
    }

    for index, item in enumerate(
        records,
        start=1,
    ):

        item_id = item.get(
            "id"
        )

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

        if not item.get(
            "title"
        ):

            raise ValueError(
                f"{item_id}: missing title"
            )

        tags = item.get(
            "tags"
        )

        if not isinstance(
            tags,
            list,
        ):

            raise ValueError(
                f"{item_id}: "
                "tags must be a list"
            )

        provider = item.get(
            "provider"
        )

        if not isinstance(
            provider,
            dict,
        ):

            raise ValueError(
                f"{item_id}: "
                "invalid provider"
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

        source = item.get(
            "source"
        )

        if not isinstance(
            source,
            dict,
        ):

            raise ValueError(
                f"{item_id}: "
                "invalid source"
            )

        if not source.get(
            "name"
        ):

            raise ValueError(
                f"{item_id}: "
                "source name missing"
            )

        if (
            source.get(
                "verified"
            )
            is not True
        ):

            raise ValueError(
                f"{item_id}: "
                "source must be verified"
            )


# ============================================================
# SAVE
# ============================================================

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


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 64)

    print(
        "PrachinLife - "
        "Common Content Index V1.1"
    )

    print("=" * 64)

    # --------------------------------------------------------
    # LOAD DEALS
    # --------------------------------------------------------

    promotions = load_json_list(
        PROMOTIONS_FILE,
        required=True,
    )

    print(
        "Loaded promotions =",
        len(promotions),
    )

    # --------------------------------------------------------
    # LOAD EAT
    # --------------------------------------------------------

    restaurants = load_json_list(
        RESTAURANTS_FILE,
        required=False,
    )

    print(
        "Loaded Eat records =",
        len(restaurants),
    )

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    index_records: list[
        dict[str, Any]
    ] = []

    for promotion in promotions:

        index_records.append(
            map_promotion(
                promotion
            )
        )

    for restaurant in restaurants:

        index_records.append(
            map_restaurant(
                restaurant
            )
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    index_records.sort(
        key=lambda item:
            (
                item.get(
                    "collected_at"
                )
                or ""
            ),
        reverse=True,
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    validate_index(
        index_records
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        index_records,
    )

    save_json(
        FRONTEND_FILE,
        index_records,
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    content_counts: dict[
        str,
        int,
    ] = {}

    category_counts: dict[
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

        category_key = (
            f"{content_type}:"
            f"{item.get('category') or 'unknown'}"
        )

        category_counts[
            category_key
        ] = (
            category_counts.get(
                category_key,
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
        "Category counts =",
        category_counts,
    )

    print()

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
        "SCHEMA VERSION =",
        SCHEMA_VERSION,
    )

    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
