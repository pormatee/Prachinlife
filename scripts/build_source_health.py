from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_DIR = PROJECT_ROOT / "data" / "meta"
OUTPUT_FILE = META_DIR / "sources.json"

SOURCES = {
    "bigc": META_DIR / "bigc.json",
    "lotus": META_DIR / "lotus.json",
    "cjmore": META_DIR / "cjmore.json",
}


def load_meta(path: Path) -> dict:
    if not path.exists():
        return {
            "status": "unknown",
            "record_count": 0,
            "last_attempt_at": None,
            "last_success_at": None,
            "last_error": "meta file missing",
        }

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path} must contain a JSON object"
        )

    return data


def determine_overall_status(
    sources: dict[str, dict],
) -> str:

    statuses = [
        item.get("status", "unknown")
        for item in sources.values()
    ]

    if statuses and all(
        status == "fresh"
        for status in statuses
    ):
        return "healthy"

    if any(
        status == "fresh"
        for status in statuses
    ):
        return "degraded"

    return "stale"


def main() -> None:

    print("=" * 60)
    print(
        "PrachinLife - Source Health Aggregator V1"
    )
    print("=" * 60)

    sources: dict[str, dict] = {}

    for name, path in SOURCES.items():

        meta = load_meta(path)

        sources[name] = {
            "status":
                meta.get("status", "unknown"),

            "record_count":
                meta.get("record_count", 0),

            "last_attempt_at":
                meta.get("last_attempt_at"),

            "last_success_at":
                meta.get("last_success_at"),

            "last_error":
                meta.get("last_error"),
        }

    output = {
        "overall_status":
            determine_overall_status(
                sources
            ),

        "sources":
            sources,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "Overall status =",
        output["overall_status"],
    )

    for name, item in sources.items():

        print(
            f"{name}: "
            f"{item['status']} "
            f"({item['record_count']} records)"
        )

    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print()
    print(
        "FINAL RESULT: PASS"
    )


if __name__ == "__main__":
    main()
