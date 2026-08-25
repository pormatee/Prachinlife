from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_URL = "https://www.cjmore.co.th/promotion"

RAW_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cjmore.json"
)

META_FILE = (
    PROJECT_ROOT
    / "data"
    / "meta"
    / "cjmore.json"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126 Safari/537.36"
    ),
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

TIMEOUT = 30


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    return data


def load_meta() -> dict:
    if not META_FILE.exists():
        return {}

    try:
        with META_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_json(path: Path, data) -> None:
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


def download_page() -> str:
    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    if not response.text.strip():
        raise RuntimeError(
            "CJ MORE promotion page is empty"
        )

    return response.text


def clean_text(value: str | None) -> str:
    return " ".join(
        (value or "").split()
    ).strip()


def absolute_url(value: str | None) -> str:
    value = clean_text(value)

    if not value:
        return ""

    return urljoin(
        SOURCE_URL,
        value,
    )


def is_ebook_url(url: str) -> bool:
    normalized = url.lower()

    return (
        "cjmore.co.th" in normalized
        and "/upload/promotion/e-book/" in normalized
        and "index.html" in normalized
    )


def make_source_id(
    title: str,
    destination_url: str,
) -> str:
    seed = (
        f"{title}|{destination_url}"
    ).encode("utf-8")

    digest = hashlib.sha256(
        seed
    ).hexdigest()[:16]

    return f"cjmore-{digest}"


def get_container_title(anchor) -> str:
    candidates = []

    container = anchor

    for _ in range(5):
        if container is None:
            break

        text = clean_text(
            container.get_text(
                " ",
                strip=True,
            )
        )

        if text:
            candidates.append(text)

        container = container.parent

    bad = {
        "",
        "โปรโมชั่น",
        "promotion",
        "ดูรายละเอียด",
        "รายละเอียด",
        "อ่านเพิ่มเติม",
    }

    for value in candidates:
        lowered = value.lower()

        if lowered in bad:
            continue

        if len(value) < 4:
            continue

        # ตัดข้อความ navigation/footer ที่ยาวผิดปกติ
        if len(value) > 300:
            continue

        return value

    return ""


def get_container_image(anchor) -> str:
    container = anchor

    for _ in range(5):
        if container is None:
            break

        image = container.find("img")

        if image is not None:
            for attr in (
                "src",
                "data-src",
                "data-original",
                "data-lazy-src",
            ):
                url = absolute_url(
                    image.get(attr)
                )

                if url:
                    return url

        container = container.parent

    return ""


def classify_raw_type(title: str) -> str:
    lowered = title.lower()

    if (
        "สมาชิก" in title
        or "สบายการ์ด" in title
        or "member" in lowered
    ):
        return "member_offer"

    if (
        "คูปอง" in title
        or "coupon" in lowered
    ):
        return "coupon"

    return "campaign"


def collect_cjmore_raw() -> list[dict]:
    html = download_page()

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    records: list[dict] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        destination_url = absolute_url(
            anchor.get("href")
        )

        if not is_ebook_url(
            destination_url
        ):
            continue

        if destination_url in seen_urls:
            continue

        title = get_container_title(
            anchor
        )

        if not title:
            # fail closed:
            # ไม่มี title ที่ยืนยันจาก DOM
            continue

        image_url = get_container_image(
            anchor
        )

        seen_urls.add(
            destination_url
        )

        records.append(
            {
                "source_id": make_source_id(
                    title,
                    destination_url,
                ),
                "source_provider": "cjmore",
                "source_page": SOURCE_URL,
                "title": title,
                "image_url": image_url or None,
                "destination_url": destination_url,
                "raw_type": classify_raw_type(
                    title
                ),
                "collected_at": None,
            }
        )

    print(
        f"Found {len(records)} "
        "CJ MORE official promotion records"
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

    timestamp = now_iso()

    result = []

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
                or timestamp
            )
        else:
            item["collected_at"] = (
                timestamp
            )

        result.append(item)

    return result


def write_meta_success(
    record_count: int,
) -> None:
    previous = load_meta()
    timestamp = now_iso()

    save_json(
        META_FILE,
        {
            "source": "cjmore",
            "status": "fresh",
            "last_attempt_at": timestamp,
            "last_success_at": timestamp,
            "record_count": record_count,
            "last_error": None,
            "previous_status": previous.get(
                "status"
            ),
        },
    )


def write_meta_failure(
    error: Exception,
    record_count: int,
) -> None:
    previous = load_meta()

    save_json(
        META_FILE,
        {
            "source": "cjmore",
            "status": "stale",
            "last_attempt_at": now_iso(),
            "last_success_at": previous.get(
                "last_success_at"
            ),
            "record_count": record_count,
            "last_error": str(error),
            "previous_status": previous.get(
                "status"
            ),
        },
    )


def main() -> None:
    print("=" * 60)
    print(
        "PrachinLife - "
        "CJ MORE Raw Collector V1"
    )
    print("=" * 60)

    existing = load_json_list(
        RAW_OUTPUT_FILE
    )

    try:
        new_records = (
            collect_cjmore_raw()
        )

        if not new_records:
            raise RuntimeError(
                "No valid CJ MORE "
                "official promotion records found"
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

        print(
            f"Records = {len(records)}"
        )
        print(
            "Source status = fresh"
        )
        print(
            "FINAL RESULT: PASS"
        )

    except Exception as error:
        write_meta_failure(
            error,
            len(existing),
        )

        print(
            "CJ MORE collection failed:",
            error,
        )
        print(
            "FINAL RESULT: FAIL_CLOSED"
        )

        raise


if __name__ == "__main__":
    main()
