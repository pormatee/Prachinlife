from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# =========================================================
# PrachinLife
# Big C Raw Collector V5
#
# Responsibility:
# - Fetch Big C official promotion page
# - Extract raw campaign records
# - Save only to data/raw/bigc.json
# - Never write normalized/promotions.json
# - Never write frontend promotions.json
# =========================================================


SOURCE_URL = "https://corporate.bigc.co.th/promotions-bigc?lang=th"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "bigc.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(
        value.split()
    ).strip()


def normalize_url(
    url: str | None,
) -> str:

    if not url:
        return ""

    return urljoin(
        SOURCE_URL,
        url.strip(),
    )


def make_source_id(
    source_url: str,
    title: str,
) -> str:

    raw_value = (
        f"{source_url}|{title}"
    )

    digest = hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()[:16]

    return f"bigc-{digest}"


def download_page() -> str:

    print(
        "🌐 Loading Big C promotions..."
    )

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    print(
        f"✅ Big C page downloaded "
        f"({len(response.text)} chars)"
    )

    return response.text


def extract_title(card) -> str:

    image = card.find("img")

    if image:

        alt = clean_text(
            image.get("alt")
        )

        if alt:
            return alt

    text = clean_text(
        card.get_text(
            " ",
            strip=True,
        )
    )

    return (
        text
        .replace(
            "ดูเพิ่มเติม",
            "",
        )
        .strip()
    )


def extract_image_url(card) -> str:

    image = card.find("img")

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

    if raw_image.startswith(
        "data:image"
    ):
        return ""

    return normalize_url(
        raw_image
    )


def extract_destination_url(card) -> str:

    links = card.find_all(
        "a",
        href=True,
    )

    for link in links:

        href = clean_text(
            link.get("href")
        )

        if (
            "linebc.bigc.co.th/catalog/"
            in href
        ):
            return normalize_url(
                href
            )

    for link in links:

        href = clean_text(
            link.get("href")
        )

        if href:
            return normalize_url(
                href
            )

    return ""


def is_valid_raw_campaign(
    title: str,
    source_url: str,
) -> bool:

    if not title:
        return False

    if not source_url:
        return False

    bad_titles = {
        "โปรโมชั่น",
        "ดูเพิ่มเติม",
        "ทั้งหมด",
        "บิ๊กซี",
        "big c",
    }

    if (
        title.strip().lower()
        in {
            item.lower()
            for item in bad_titles
        }
    ):
        return False

    return len(
        title.strip()
    ) >= 5


def collect_bigc_raw() -> list[dict]:

    html = download_page()

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    cards = soup.select(
        "div.promotion-box"
    )

    print(
        f"🔎 Found {len(cards)} "
        f"promotion cards"
    )

    raw_records: list[dict] = []

    seen_urls: set[str] = set()

    collected_at = (
        datetime.now()
        .astimezone()
        .isoformat()
    )

    for card in cards:

        title = extract_title(
            card
        )

        source_url = (
            extract_destination_url(
                card
            )
        )

        image_url = (
            extract_image_url(
                card
            )
        )

        if not is_valid_raw_campaign(
            title,
            source_url,
        ):
            continue

        if source_url in seen_urls:
            continue

        seen_urls.add(
            source_url
        )

        record = {
            "source_id":
                make_source_id(
                    source_url,
                    title,
                ),

            "source_provider":
                "bigc",

            "source_page":
                SOURCE_URL,

            "title":
                title,

            "image_url":
                image_url,

            "destination_url":
                source_url,

            "raw_type":
                "campaign",

            "collected_at":
                collected_at,
        }

        raw_records.append(
            record
        )

        print()
        print(
            "RAW:",
            title
        )
        print(
            "URL:",
            source_url
        )
        print(
            "IMAGE:",
            image_url
            or "NO IMAGE"
        )

    print()

    print(
        f"✅ Found {len(raw_records)} "
        f"clean raw Big C campaigns"
    )

    return raw_records


def save_raw(
    records: list[dict],
) -> None:

    RAW_OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RAW_OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "💾 Saved raw data:",
        RAW_OUTPUT_FILE
    )


def main() -> None:

    print(
        "=" * 60
    )

    print(
        "PrachinLife - Big C Raw Collector V5"
    )

    print(
        "=" * 60
    )

    try:

        records = collect_bigc_raw()

        if not records:

            print()
            print(
                "⚠️ No Big C campaigns found."
            )
            print(
                "Existing raw file preserved."
            )

            return

        save_raw(
            records
        )

        print()
        print(
            "✅ Big C Raw Collector V5 completed"
        )
        print(
            f"📦 Raw records = "
            f"{len(records)}"
        )

    except Exception as error:

        print()
        print(
            "❌ Big C Raw Collector V5 failed:"
        )
        print(error)
        print()
        print(
            "Existing raw file preserved."
        )


if __name__ == "__main__":
    main()
