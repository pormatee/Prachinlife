from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_INPUT = Path(
    "data/web_discovery/vegetarian_search_results.json"
)

DEFAULT_OUTPUT = Path(
    "data/candidates/vegetarian_web_candidates.json"
)


STRONG_KEYWORDS = [
    "อาหารเจ",
    "ร้านเจ",
    "ข้าวเจ",
    "โรงเจ",
    "เจจริง",
    "เจแท้",
    "มังสวิรัติ",
    "vegetarian",
    "vegan",
]

OPTION_KEYWORDS = [
    "เมนูเจ",
    "เมนูมังสวิรัติ",
    "vegetarian option",
    "vegetarian options",
    "vegan option",
    "vegan options",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "PrachinLife Vegetarian "
            "Web Discovery V1"
        )
    )

    parser.add_argument(
        "--province",
        required=True,
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    return parser.parse_args()


def clean_text(value):
    if value is None:
        return ""

    return " ".join(
        str(value).strip().split()
    )


def normalize_url(value):
    value = clean_text(value)

    if not value:
        return ""

    parsed = urlparse(value)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return ""

    return value


def make_id(
    province,
    title,
    source_url,
):
    raw = (
        f"{province}|"
        f"{title}|"
        f"{source_url}"
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return f"web-{digest}"


def classify_text(
    title,
    snippet,
):
    text = (
        f"{title} {snippet}"
    ).lower()

    strong_match = any(
        keyword in text
        for keyword in STRONG_KEYWORDS
    )

    option_match = any(
        keyword in text
        for keyword in OPTION_KEYWORDS
    )

    # กัน false positive เจ๊ / เจ้า / เจริญ
    jay_shop_match = bool(
        re.search(
            r"ร้าน\s*เจ(?![่้๊๋า-ูเ-์])",
            text,
        )
    )

    if (
        strong_match
        or jay_shop_match
    ):
        return (
            "named_candidate",
            "web_text_strong_vegetarian_signal",
        )

    if option_match:
        return (
            "option_available",
            "web_text_vegetarian_option_signal",
        )

    return (
        "unknown",
        "insufficient_web_evidence",
    )


def infer_source_name(
    source_url,
    explicit_source,
):
    explicit_source = clean_text(
        explicit_source
    )

    if explicit_source:
        return explicit_source

    try:
        host = urlparse(
            source_url
        ).netloc.lower()

        host = host.removeprefix(
            "www."
        )

        return host or "Web"

    except Exception:
        return "Web"


def normalize_record(
    raw,
    province,
):
    if not isinstance(raw, dict):
        return None

    title = clean_text(
        raw.get("title")
    )

    snippet = clean_text(
        raw.get("snippet")
        or raw.get("description")
    )

    source_url = normalize_url(
        raw.get("url")
        or raw.get("source_url")
    )

    if not title or not source_url:
        return None

    tier, evidence_reason = (
        classify_text(
            title,
            snippet,
        )
    )

    if tier == "unknown":
        return None

    latitude = raw.get(
        "latitude"
    )

    longitude = raw.get(
        "longitude"
    )

    if not isinstance(
        latitude,
        (int, float),
    ):
        latitude = None

    if not isinstance(
        longitude,
        (int, float),
    ):
        longitude = None

    source = infer_source_name(
        source_url,
        raw.get("source"),
    )

    needs_location_review = (
        latitude is None
        or longitude is None
    )

    return {
        "id": make_id(
            province,
            title,
            source_url,
        ),
        "title": title,
        "content_type":
            "vegetarian",
        "food_types": [
            "vegetarian"
        ],
        "location": {
            "province":
                province,
            "district":
                clean_text(
                    raw.get("district")
                )
                or None,
            "subdistrict":
                clean_text(
                    raw.get(
                        "subdistrict"
                    )
                )
                or None,
            "country":
                "TH",
            "latitude":
                latitude,
            "longitude":
                longitude,
        },
        "metadata": {
            "display_tier":
                tier,
            "show_in_primary_directory":
                False,
            "needs_review":
                True,
            "review_reason":
                (
                    "web_discovery_"
                    "needs_verification"
                ),
            "evidence_reason":
                evidence_reason,
            "diet_vegetarian":
                None,
            "diet_vegan":
                None,
            "web_snippet":
                snippet or None,
            "location_needs_review":
                needs_location_review,
        },
        "source":
            source,
        "source_url":
            source_url,
        "collected_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


def deduplicate(
    records,
):
    unique = {}

    for item in records:
        key = (
            clean_text(
                item.get("title")
            ).lower(),
            clean_text(
                (
                    item.get(
                        "location"
                    )
                    or {}
                ).get(
                    "province"
                )
            ).lower(),
        )

        existing = unique.get(
            key
        )

        if existing is None:
            unique[key] = item
            continue

        old_url = (
            existing.get(
                "source_url"
            )
            or ""
        )

        new_url = (
            item.get(
                "source_url"
            )
            or ""
        )

        if len(new_url) < len(old_url):
            unique[key] = item

    return list(
        unique.values()
    )


def main():
    args = parse_args()

    province = clean_text(
        args.province
    )

    if not province:
        raise SystemExit(
            "ERROR: province required"
        )

    input_path = Path(
        args.input
    )

    output_path = Path(
        args.output
    )

    if not input_path.exists():
        raise SystemExit(
            f"ERROR: input not found: "
            f"{input_path}"
        )

    raw = json.loads(
        input_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(raw, list):
        raise SystemExit(
            "ERROR: input must be array"
        )

    records = []

    rejected = 0

    for item in raw:
        record = normalize_record(
            item,
            province,
        )

        if record is None:
            rejected += 1
            continue

        records.append(record)

    records = deduplicate(
        records
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            records,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    tiers = {}

    for item in records:
        tier = (
            item.get("metadata")
            or {}
        ).get("display_tier")

        tiers[tier] = (
            tiers.get(tier, 0)
            + 1
        )

    print("=" * 60)
    print(
        "VEGETARIAN WEB DISCOVERY V1"
    )
    print("=" * 60)

    print(
        "Province =",
        province,
    )

    print(
        "Input =",
        len(raw),
    )

    print(
        "Accepted =",
        len(records),
    )

    print(
        "Rejected =",
        rejected,
    )

    print(
        "Tiers =",
        tiers,
    )

    print()

    for item in records:
        print(
            item["metadata"][
                "display_tier"
            ],
            "|",
            item["title"],
            "|",
            item["source"],
        )

    print()
    print(
        "Saved =",
        output_path,
    )


if __name__ == "__main__":
    main()
