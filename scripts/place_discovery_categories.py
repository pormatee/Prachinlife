from __future__ import annotations

import json
from pathlib import Path


DEFAULT_CATEGORY_CONFIG = Path(
    "data/config/place_categories.json"
)


def load_category_configs(
    path: Path = DEFAULT_CATEGORY_CONFIG,
):
    if not path.exists():
        raise FileNotFoundError(
            f"Category config not found: {path}"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Category config must be an object"
        )

    return data


def get_category_config(
    category,
    path: Path = DEFAULT_CATEGORY_CONFIG,
):
    configs = load_category_configs(
        path
    )

    config = configs.get(
        category
    )

    if not isinstance(
        config,
        dict,
    ):
        raise KeyError(
            f"Category not configured: {category}"
        )

    return config


def build_regex_union(
    values,
):
    cleaned = [
        str(value).strip()
        for value in values
        if str(value).strip()
    ]

    return "|".join(
        cleaned
    )


def get_osm_amenity_regex(
    category,
):
    config = get_category_config(
        category
    )

    amenities = (
        config.get("osm")
        or {}
    ).get(
        "amenities",
        [],
    )

    return build_regex_union(
        amenities
    )


def get_query_keyword_regex(
    category,
    *,
    thai_only=False,
):
    config = get_category_config(
        category
    )

    keywords = (
        config.get("keywords")
        or {}
    )

    key = (
        "thai_query"
        if thai_only
        else "all_query"
    )

    return build_regex_union(
        keywords.get(
            key,
            [],
        )
    )
