from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PROVINCE_CONFIG = Path(
    "data/config/thailand_provinces.json"
)


def load_province_configs(
    path: Path = DEFAULT_PROVINCE_CONFIG,
):
    if not path.exists():
        raise FileNotFoundError(
            f"Province config not found: {path}"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise ValueError(
            "Province config must be an object"
        )

    return data


def get_province_config(
    province: str,
    path: Path = DEFAULT_PROVINCE_CONFIG,
):
    configs = load_province_configs(path)

    config = configs.get(province)

    if not isinstance(config, dict):
        raise KeyError(
            f"Province not configured: {province}"
        )

    bbox = config.get("bbox")

    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
    ):
        raise ValueError(
            f"Invalid bbox for {province}"
        )

    aliases = config.get("aliases") or []

    return {
        "province": province,
        "aliases": aliases,
        "bbox": bbox,
    }


def split_bbox(
    bbox,
    rows=2,
    cols=2,
):
    if (
        not isinstance(bbox, (list, tuple))
        or len(bbox) != 4
    ):
        raise ValueError(
            "bbox must be [south, west, north, east]"
        )

    if rows < 1 or cols < 1:
        raise ValueError(
            "rows and cols must be >= 1"
        )

    south, west, north, east = map(
        float,
        bbox,
    )

    lat_step = (
        north - south
    ) / rows

    lon_step = (
        east - west
    ) / cols

    grids = []

    for row in range(rows):
        grid_south = (
            south + row * lat_step
        )

        grid_north = (
            south + (row + 1) * lat_step
        )

        for col in range(cols):
            grid_west = (
                west + col * lon_step
            )

            grid_east = (
                west + (col + 1) * lon_step
            )

            grids.append(
                [
                    grid_south,
                    grid_west,
                    grid_north,
                    grid_east,
                ]
            )

    return grids


def point_in_bbox(
    latitude,
    longitude,
    bbox,
):
    south, west, north, east = bbox

    return (
        south <= latitude <= north
        and
        west <= longitude <= east
    )


def point_in_province_bbox(
    latitude,
    longitude,
    province,
    path: Path = DEFAULT_PROVINCE_CONFIG,
):
    config = get_province_config(
        province,
        path,
    )

    return point_in_bbox(
        latitude,
        longitude,
        config["bbox"],
    )
