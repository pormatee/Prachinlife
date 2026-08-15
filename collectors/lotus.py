from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


# =========================================================
# PrachinLife
# Lotus's Raw Collector V1
#
# Responsibility:
# - Collect promotion cards from My Lotus's official page
# - Extract title and original image URL
# - Preserve source-page provenance
# - Do not invent detail URLs, prices, dates, or locations
# =========================================================


SOURCE_URL = "https://my.lotuss.com/promotions/th"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "lotus.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language":
        "th-TH,th;q=0.9,en;q=0.8",
}


# =========================================================
# HELPERS
# =========================================================


def clean_text(
    value: str | None,
) -> str:

    if not value:
        return ""

    return " ".join(
        value.split()
    ).strip()


def make_source_id(
    title: str,
    image_url: str,
) -> str:

    raw_value = (
        f"{title}|{image_url}"
    )

    digest = hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()[:16]

    return f"lotus-{digest}"


def extract_original_image_url(
    src: str | None,
) -> str:

    if not src:
        return ""

    src = src.strip()

    # Next.js image proxy:
    # /_next/image?url=<encoded-original-url>&w=640&q=75
    if src.startswith("/_next/image"):

        parsed = urlparse(
            src
        )

        query = parse_qs(
            parsed.query
        )

        values = query.get(
            "url"
        )

        if values:

            return unquote(
                values[0]
            )

    if src.startswith(
        "http://"
    ) or src.startswith(
        "https://"
    ):
        return src

    return ""


# =========================================================
# DOWNLOAD
# =========================================================


def download_page() -> str:

    print(
        "🌐 Loading Lotus's promotions..."
    )

    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    print(
        f"✅ Lotus's page downloaded "
        f"({len(response.text)} chars)"
    )

    print(
        "FINAL URL:",
        response.url,
    )

    return response.text


# =========================================================
# CARD EXTRACTION
# =========================================================


def get_card_title(card) -> str:

    image = card.find("img")

    if image:

        alt = clean_text(
            image.get("alt")
        )

        if alt:
            return alt


    detail = card.select_one(
        ".detail"
    )

    if detail:

        text = clean_text(
            detail.get_text(
                " ",
                strip=True,
            )
        )

        if text:
            return text


    return clean_text(
        card.get_text(
            " ",
            strip=True,
        )
    )


def get_card_image(card) -> str:

    image = card.find("img")

    if not image:
        return ""

    src = (
        image.get("src")
        or ""
    )

    return extract_original_image_url(
        src
    )


def is_valid_card(
    title: str,
    image_url: str,
) -> bool:

    if not title:
        return False

    if len(
        title.strip()
    ) < 4:
        return False

    if not image_url:
        return False

    bad_titles = {
        "โปรโมชั่น",
        "ทั้งหมด",
        "ดูเพิ่มเติม",
        "sort",
        "icon",
    }

    normalized = (
        title
        .strip()
        .lower()
    )

    if normalized in {
        item.lower()
        for item in bad_titles
    }:
        return False

    return True


# =========================================================
# CLASSIFICATION HINT
# =========================================================


def classify_raw_type(
    title: str,
) -> str:

    normalized = (
        title
        .lower()
    )

    if (
        "คูปอง" in normalized
        or "coupon" in normalized
    ):
        return "coupon"

    if (
        "สมาชิก" in normalized
        or "member" in normalized
        or "my lotus" in normalized
        or "มายโลตัส" in normalized
    ):
        return "member_offer"

    return "campaign"


# =========================================================
# COLLECT
# =========================================================


def collect_lotus_raw() -> list[dict]:

    html = download_page()

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    cards = soup.select(
        "a.card-pro"
    )

    print(
        f"🔎 Found {len(cards)} "
        f"Lotus's promotion cards"
    )

    records: list[dict] = []

    seen_ids: set[str] = set()

    collected_at = (
        datetime.now()
        .astimezone()
        .isoformat()
    )


    for card in cards:

        title = get_card_title(
            card
        )

        image_url = get_card_image(
            card
        )

        if not is_valid_card(
            title,
            image_url,
        ):
            continue


        source_id = make_source_id(
            title,
            image_url,
        )


        if source_id in seen_ids:
            continue


        seen_ids.add(
            source_id
        )


        record = {

            "source_id":
                source_id,

            "source_provider":
                "lotus",

            "source_page":
                SOURCE_URL,

            "title":
                title,

            "image_url":
                image_url,

            "destination_url":
                None,

            "raw_type":
                classify_raw_type(
                    title
                ),

            "collected_at":
                collected_at,
        }


        records.append(
            record
        )


        print()

        print(
            "RAW:",
            title
        )

        print(
            "TYPE:",
            record["raw_type"]
        )

        print(
            "IMAGE:",
            image_url
        )


    print()

    print(
        f"✅ Found {len(records)} "
        f"clean Lotus's promotion records"
    )

    return records


# =========================================================
# SAVE
# =========================================================


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


# =========================================================
# MAIN
# =========================================================


def main() -> None:

    print(
        "=" * 60
    )

    print(
        "PrachinLife - Lotus's Raw Collector V1"
    )

    print(
        "=" * 60
    )


    try:

        records = collect_lotus_raw()


        if not records:

            print()

            print(
                "⚠️ No Lotus's promotions found."
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
            "✅ Lotus's Raw Collector V1 completed"
        )

        print(
            f"📦 Raw records = "
            f"{len(records)}"
        )


    except Exception as error:

        print()

        print(
            "❌ Lotus's Raw Collector V1 failed:"
        )

        print(error)

        print()

        print(
            "Existing raw file preserved."
        )


if __name__ == "__main__":
    main()
