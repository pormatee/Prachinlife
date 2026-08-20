from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_OUTPUT = Path(
    "data/web_discovery/vegetarian_queries.json"
)


QUERY_PATTERNS = [
    "ร้านอาหารเจ {province}",
    "ร้านเจ {province}",
    "อาหารเจ {province}",
    "ข้าวเจ {province}",
    "ร้านมังสวิรัติ {province}",
    "อาหารมังสวิรัติ {province}",
    "vegetarian restaurant {province}",
    "vegan restaurant {province}",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build PrachinLife vegetarian "
            "web discovery queries"
        )
    )

    parser.add_argument(
        "--province",
        required=True,
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    return parser.parse_args()


def clean_text(value):
    return " ".join(
        str(value or "")
        .strip()
        .split()
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

    output_path = Path(
        args.output
    )

    queries = []

    for index, pattern in enumerate(
        QUERY_PATTERNS,
        start=1,
    ):
        query = pattern.format(
            province=province
        )

        queries.append(
            {
                "id":
                    f"{province}-{index}",
                "province":
                    province,
                "query":
                    query,
                "category":
                    "vegetarian",
                "status":
                    "pending",
            }
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            queries,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("=" * 60)
    print(
        "VEGETARIAN WEB QUERY GENERATOR"
    )
    print("=" * 60)

    print(
        "Province =",
        province,
    )

    print(
        "Queries =",
        len(queries),
    )

    print()

    for item in queries:
        print(
            "-",
            item["query"],
        )

    print()
    print(
        "Saved =",
        output_path,
    )


if __name__ == "__main__":
    main()
