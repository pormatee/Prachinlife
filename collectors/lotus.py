from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://my.lotuss.com/promotions/th"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "lotus.json"
)

META_FILE = (
    PROJECT_ROOT
    / "data"
    / "meta"
    / "lotus.json"
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
            f"🌐 Lotus's fetch attempt "
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

            print(
                "FINAL URL =",
                response.url,
            )

            if response.status_code == 200:

                print(
                    f"✅ Lotus's page downloaded "
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
        f"Lotus's download failed: "
        f"{last_error}"
    )


def extract_original_image_url(
    src: str | None,
) -> str:

    if not src:
        return ""

    src = src.strip()

    if src.startswith(
        "/_next/image"
    ):

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

    if (
        src.startswith("http://")
        or src.startswith("https://")
    ):
        return src

    return ""


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

    return (
        extract_original_image_url(
            src
        )
    )


def is_valid_card(
    title: str,
    image_url: str,
) -> bool:

    if not title:
        return False

    if not image_url:
        return False

    if len(
        title.strip()
    ) < 4:
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

    return (
        normalized
        not in {
            item.lower()
            for item in bad_titles
        }
    )


def classify_raw_type(
    title: str,
) -> str:

    normalized = (
        title.lower()
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

        records.append(
            {
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
                    None,
            }
        )

    print(
        f"✅ Found {len(records)} "
        f"clean Lotus's promotion records"
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

        source_id = item.get(
            "source_id"
        )

        old = old_by_id.get(
            source_id
        )

        if old:

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
            "lotus",

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
            "lotus",

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
        "Lotus's Raw Collector V1.1"
    )

    print("=" * 60)

    existing = load_json_list(
        RAW_OUTPUT_FILE
    )

    try:

        new_records = (
            collect_lotus_raw()
        )

        if not new_records:

            raise RuntimeError(
                "No valid Lotus's "
                "promotion records found"
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

        counts: dict[str, int] = {}

        for item in records:

            raw_type = (
                item.get("raw_type")
                or "unknown"
            )

            counts[raw_type] = (
                counts.get(
                    raw_type,
                    0,
                )
                + 1
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
            "Types =",
            counts,
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
            "⚠️ Lotus's collection failed:"
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

        print()
        print(
            "FINAL RESULT: STALE_OK"
        )


if __name__ == "__main__":
    main()
