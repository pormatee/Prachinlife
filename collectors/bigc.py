from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# =========================================================
# PromoPrachin
# Big C Promotion Collector V1
# =========================================================

SOURCE_URL = "https://corporate.bigc.co.th/promotion"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "promotions.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    )
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def make_id(value: str) -> str:
    digest = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:16]

    return f"bigc-{digest}"


def load_existing_promotions() -> list[dict]:
    if not OUTPUT_FILE.exists():
        return []

    try:
        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            if isinstance(data, dict):
                return data.get(
                    "promotions",
                    []
                )

    except Exception as error:
        print(
            "⚠️ Cannot read promotions.json:",
            error
        )

    return []


def download_page() -> str:
    print(
        "🌐 Loading Big C promotions..."
    )

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    print(
        "✅ Big C page downloaded"
    )

    return response.text


def collect_bigc_promotions() -> list[dict]:
    html = download_page()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    promotions = []
    seen_urls = set()

    links = soup.find_all(
        "a",
        href=True
    )

    for link in links:

        href = clean_text(
            link.get("href")
        )

        if not href:
            continue

        full_url = urljoin(
            SOURCE_URL,
            href
        )

        url_lower = full_url.lower()

        if (
            "promotion" not in url_lower
            and "campaign" not in url_lower
            and "promo" not in url_lower
        ):
            continue

        if full_url in seen_urls:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        image_url = ""

        image = link.find("img")

        if image:

            if not title:
                title = clean_text(
                    image.get("alt")
                )

            raw_image = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-lazy-src")
                or ""
            )

            if raw_image:
                image_url = urljoin(
                    SOURCE_URL,
                    raw_image
                )

        if not title:
            continue

        # ตัดรายการที่เป็น menu/navigation สั้นเกินไป
        if len(title) < 4:
            continue

        seen_urls.add(full_url)

        promotions.append(
            {
                "id": make_id(full_url),

                "store": "Big C",

                "product": title,

                # V1 ยังไม่เดาราคา ถ้าต้นทางไม่ได้เปิดเผย
                "old_price": 0,
                "new_price": 0,

                "expiry":
                    "ตรวจสอบรายละเอียดจาก Big C",

                "branch":
                    "ตรวจสอบสาขาที่ร่วมรายการ",

                "category":
                    "โปรโมชั่น",

                "urgent":
                    False,

                "image":
                    image_url,

                "source_url":
                    full_url,

                "source":
                    "Big C",

                "source_type":
                    "official_promotion",

                "verified":
                    False,

                "collected_at":
                    datetime.now()
                    .astimezone()
                    .isoformat(),
            }
        )

    print(
        f"✅ Found {len(promotions)} Big C promotions"
    )

    return promotions


def merge_promotions(
    existing: list[dict],
    bigc_promotions: list[dict]
) -> list[dict]:

    # ลบข้อมูล Big C เก่าออก
    # แต่เก็บ Lotus / CJ More / ร้านอื่นไว้
    other_stores = [
        item
        for item in existing
        if item.get("store") != "Big C"
    ]

    return (
        bigc_promotions
        + other_stores
    )


def save_promotions(
    promotions: list[dict]
) -> None:

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            promotions,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "💾 Saved:",
        OUTPUT_FILE
    )


def main() -> None:

    print("=" * 60)
    print(
        "PromoPrachin - Big C Collector V1"
    )
    print("=" * 60)

    existing = load_existing_promotions()

    try:

        bigc_promotions = (
            collect_bigc_promotions()
        )

        # ป้องกันข้อมูลเดิมถูกลบทิ้ง
        # ถ้าเว็บ Big C เปลี่ยนโครงสร้าง
        if not bigc_promotions:

            print()
            print(
                "⚠️ No Big C promotions found."
            )

            print(
                "Existing promotions.json preserved."
            )

            return

        merged = merge_promotions(
            existing,
            bigc_promotions
        )

        save_promotions(
            merged
        )

        print()
        print(
            "✅ Big C Collector completed"
        )

        print(
            f"📦 Total records = {len(merged)}"
        )

    except Exception as error:

        print()
        print(
            "❌ Big C Collector failed:"
        )

        print(error)

        print()
        print(
            "Existing promotions.json preserved."
        )


if __name__ == "__main__":
    main()
