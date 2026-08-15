from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://corporate.bigc.co.th/promotions-bigc?lang=th"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "promotions.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    ),
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


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
    print("🌐 Loading Big C promotions...")

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    print(
        f"✅ Big C page downloaded "
        f"({len(response.text)} chars)"
    )

    return response.text


def is_bad_title(title: str) -> bool:
    bad_titles = {
        "ทั้งหมด",
        "บิ๊กซี",
        "บิ๊กซีมินิ",
        "ร้านยาเพรียว",
        "บิ๊กซีพลาซ่า",
        "ดูเพิ่มเติม",
        "โปรโมชั่น",
        "promotion",
        "big c",
    }

    normalized = title.strip().lower()

    if normalized in bad_titles:
        return True

    if len(normalized) < 5:
        return True

    return False


def get_image_url(link) -> str:
    image = link.find("img")

    if not image:
        return ""

    raw_image = (
        image.get("src")
        or image.get("data-src")
        or image.get("data-lazy-src")
        or image.get("data-original")
        or ""
    )

    if not raw_image:
        return ""

    return urljoin(
        SOURCE_URL,
        raw_image
    )


def get_title(link) -> str:
    title = clean_text(
        link.get_text(
            " ",
            strip=True
        )
    )

    image = link.find("img")

    if image:

        alt = clean_text(
            image.get("alt")
        )

        # alt ของรูปมักให้ชื่อโปรโมชั่นสะอาดกว่า
        if alt and len(alt) > len(title):
            title = alt

    # ลบคำ "ดูเพิ่มเติม"
    title = re.sub(
        r"\s*ดูเพิ่มเติม\s*$",
        "",
        title,
        flags=re.IGNORECASE
    )

    return clean_text(title)


def collect_bigc_promotions() -> list[dict]:
    html = download_page()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    promotions = []
    seen_titles = set()
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

        title = get_title(link)

        if not title:
            continue

        if is_bad_title(title):
            continue

        url_lower = full_url.lower()

        # ต้องเกี่ยวข้องกับ promotion
        if (
            "promotion" not in url_lower
            and "campaign" not in url_lower
        ):
            continue

        # ป้องกันรายการซ้ำ
        normalized_title = title.lower()

        if normalized_title in seen_titles:
            continue

        if full_url in seen_urls:
            continue

        image_url = get_image_url(link)

        seen_titles.add(
            normalized_title
        )

        seen_urls.add(
            full_url
        )

        promotion = {
            "id": make_id(
                full_url + title
            ),

            "store": "Big C",

            "product": title,

            # V2 ไม่เดาราคา
            "old_price": 0,
            "new_price": 0,

            "expiry":
                "ตรวจสอบรายละเอียดจาก Big C",

            "branch":
                "Big C / ตรวจสอบสาขาที่ร่วมรายการ",

            "category":
                "โปรโมชั่น",

            "urgent":
                False,

            "image":
                image_url,

            "source_url":
                full_url,

            "source":
                "Big C Official",

            "source_type":
                "official_promotion",

            "verified":
                True,

            "collected_at":
                datetime.now()
                .astimezone()
                .isoformat(),
        }

        promotions.append(
            promotion
        )

    print(
        f"✅ Found {len(promotions)} "
        f"clean Big C promotions"
    )

    for item in promotions:
        print(
            " •",
            item["product"]
        )

    return promotions


def merge_promotions(
    existing: list[dict],
    bigc_promotions: list[dict]
) -> list[dict]:

    # เก็บข้อมูลร้านอื่น
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
        "PromoPrachin - Big C Collector V2"
    )

    print("=" * 60)

    existing = (
        load_existing_promotions()
    )

    try:

        bigc_promotions = (
            collect_bigc_promotions()
        )

        # ป้องกันข้อมูลเดิมหาย
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
            "✅ Big C Collector V2 completed"
        )

        print(
            f"📦 Total records = "
            f"{len(merged)}"
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
