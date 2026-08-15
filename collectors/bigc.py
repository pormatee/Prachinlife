from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://corporate.bigc.co.th/promotions-bigc?lang=th"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "bigc.json"
)

META_FILE = (
    PROJECT_ROOT
    / "data"
    / "meta"
    / "bigc.json"
)


USER_AGENTS = [
    (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
]


def now_iso() -> str:
    return (
        datetime.now()
        .astimezone()
        .isoformat()
    )


def clean_text(
    value: str | None,
) -> str:

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


def load_json_list(
    path: Path,
) -> list[dict]:

    if not path.exists():
        return []

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def load_meta() -> dict:

    if not META_FILE.exists():
        return {}

    try:

        with META_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def save_json(
    path: Path,
    data,
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


def build_headers(
    user_agent: str,
) -> dict:

    return {
        "User-Agent":
            user_agent,

        "Accept":
            (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),

        "Accept-Language":
            "th-TH,th;q=0.9,en;q=0.8",

        "Cache-Control":
            "no-cache",

        "Pragma":
            "no-cache",

        "Referer":
            "https://corporate.bigc.co.th/",

        "Upgrade-Insecure-Requests":
            "1",
    }


def download_page() -> str:

    last_error: Exception | None = None

    session = requests.Session()

    for attempt in range(
        1,
        4,
    ):

        user_agent = USER_AGENTS[
            (attempt - 1)
            % len(USER_AGENTS)
        ]

        print(
            f"🌐 Big C fetch attempt "
            f"{attempt}/3"
        )

        try:

            response = session.get(
                SOURCE_URL,
                headers=build_headers(
                    user_agent
                ),
                timeout=30,
                allow_redirects=True,
            )

            print(
                "HTTP STATUS =",
                response.status_code,
            )

            if response.status_code == 200:

                print(
                    f"✅ Big C page downloaded "
                    f"({len(response.text)} chars)"
                )

                return response.text

            last_error = RuntimeError(
                f"HTTP {response.status_code}"
            )

        except Exception as error:

            last_error = error

        if attempt < 3:

            time.sleep(
                attempt * 2
            )

    raise RuntimeError(
        f"Big C download failed: "
        f"{last_error}"
    )


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


def extract_destination_url(
    card,
) -> str:

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


def is_valid_campaign(
    title: str,
    source_url: str,
) -> bool:

    if not title:
        return False

    if not source_url:
        return False

    if len(
        title.strip()
    ) < 5:
        return False

    bad_titles = {
        "โปรโมชั่น",
        "ดูเพิ่มเติม",
        "ทั้งหมด",
        "บิ๊กซี",
        "big c",
    }

    return (
        title.strip().lower()
        not in {
            item.lower()
            for item in bad_titles
        }
    )


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

    records: list[dict] = []
    seen_urls: set[str] = set()

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

        if not is_valid_campaign(
            title,
            source_url,
        ):
            continue

        if source_url in seen_urls:
            continue

        seen_urls.add(
            source_url
        )

        records.append(
            {
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

                # จะเติม collected_at
                # หลังเทียบกับข้อมูลเดิม
                "collected_at":
                    None,
            }
        )

    print(
        f"✅ Found {len(records)} "
        f"clean Big C campaigns"
    )

    return records


def content_signature(
    item: dict,
) -> tuple:

    return (
        item.get("source_id"),
        item.get("title"),
        item.get("image_url"),
        item.get("destination_url"),
        item.get("raw_type"),
    )


def preserve_stable_timestamps(
    new_records: list[dict],
    old_records: list[dict],
) -> list[dict]:

    old_by_id = {
        item.get("source_id"): item
        for item in old_records
        if item.get("source_id")
    }

    current_time = now_iso()

    result: list[dict] = []

    for item in new_records:

        old = old_by_id.get(
            item.get("source_id")
        )

        if (
            old
            and content_signature(old)
            == content_signature(item)
        ):

            item["collected_at"] = (
                old.get("collected_at")
                or current_time
            )

        else:

            item["collected_at"] = (
                current_time
            )

        result.append(
            item
        )

    return result


def write_meta_success(
    record_count: int,
) -> None:

    previous = load_meta()

    timestamp = now_iso()

    meta = {
        "source":
            "bigc",

        "status":
            "fresh",

        "last_attempt_at":
            timestamp,

        "last_success_at":
            timestamp,

        "record_count":
            record_count,

        "last_error":
            None,

        "previous_status":
            previous.get("status"),
    }

    save_json(
        META_FILE,
        meta,
    )


def write_meta_failure(
    error: Exception,
    record_count: int,
) -> None:

    previous = load_meta()

    meta = {
        "source":
            "bigc",

        "status":
            "stale",

        "last_attempt_at":
            now_iso(),

        "last_success_at":
            previous.get(
                "last_success_at"
            ),

        "record_count":
            record_count,

        "last_error":
            str(error),

        "previous_status":
            previous.get("status"),
    }

    save_json(
        META_FILE,
        meta,
    )


def main() -> None:

    print("=" * 60)

    print(
        "PrachinLife - "
        "Big C Raw Collector V5.1"
    )

    print("=" * 60)

    existing = load_json_list(
        RAW_OUTPUT_FILE
    )

    try:

        new_records = (
            collect_bigc_raw()
        )

        if not new_records:

            raise RuntimeError(
                "No valid Big C "
                "campaigns found"
            )

        records = (
            preserve_stable_timestamps(
                new_records,
                existing,
            )
        )

        save_json(
            RAW_OUTPUT_FILE,
            records,
        )

        write_meta_success(
            len(records)
        )

        print()
        print(
            "💾 Raw data saved"
        )

        print(
            f"📦 Records = "
            f"{len(records)}"
        )

        print(
            "🟢 Source status = fresh"
        )

        print()
        print(
            "FINAL RESULT: PASS"
        )

    except Exception as error:

        write_meta_failure(
            error,
            len(existing),
        )

        print()
        print(
            "⚠️ Big C collection failed:"
        )

        print(error)

        print()
        print(
            "Existing raw data preserved."
        )

        print(
            f"📦 Preserved records = "
            f"{len(existing)}"
        )

        print(
            "🟡 Source status = stale"
        )

        # ตั้งใจ exit 0:
        # source ล้มไม่ควรทำให้
        # multi-source pipeline ทั้งระบบล้ม
        print()
        print(
            "FINAL RESULT: STALE_OK"
        )


if __name__ == "__main__":
    main()
