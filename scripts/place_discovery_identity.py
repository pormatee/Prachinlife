from __future__ import annotations

import math
import re
import unicodedata


EARTH_RADIUS_KM = 6371.0088


def normalize_text(value):
    value = str(value or "").strip().lower()

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    value = re.sub(
        r"[^\wก-๙]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def get_coordinates(item):
    location = (
        item.get("location")
        or {}
    )

    lat = location.get(
        "latitude"
    )

    lon = location.get(
        "longitude"
    )

    if not isinstance(
        lat,
        (int, float),
    ):
        return None

    if not isinstance(
        lon,
        (int, float),
    ):
        return None

    return (
        float(lat),
        float(lon),
    )


def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    d_phi = math.radians(
        lat2 - lat1
    )

    d_lambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(d_phi / 2) ** 2
        +
        math.cos(phi1)
        *
        math.cos(phi2)
        *
        math.sin(d_lambda / 2) ** 2
    )

    return (
        2
        *
        EARTH_RADIUS_KM
        *
        math.asin(
            math.sqrt(a)
        )
    )


def same_province(a, b):
    province_a = normalize_text(
        (
            a.get("location")
            or {}
        ).get("province")
    )

    province_b = normalize_text(
        (
            b.get("location")
            or {}
        ).get("province")
    )

    return (
        bool(province_a)
        and
        province_a == province_b
    )


def title_key(item):
    return normalize_text(
        item.get("title")
    )


def identity_key(item):
    return (
        title_key(item),
        normalize_text(
            (
                item.get("location")
                or {}
            ).get("province")
        ),
    )


def compare_identity(
    a,
    b,
    *,
    coordinate_threshold_km=0.3,
):
    id_a = a.get("id")
    id_b = b.get("id")

    if (
        id_a
        and
        id_b
        and
        id_a == id_b
    ):
        return {
            "duplicate": True,
            "confidence": "exact",
            "reason": "same_id",
            "distance_km": 0.0,
        }

    if (
        identity_key(a)
        ==
        identity_key(b)
        and
        title_key(a)
    ):
        return {
            "duplicate": True,
            "confidence": "high",
            "reason": "same_title_province",
            "distance_km": None,
        }

    if not same_province(a, b):
        return {
            "duplicate": False,
            "confidence": "none",
            "reason": "different_province",
            "distance_km": None,
        }

    title_a = title_key(a)
    title_b = title_key(b)

    if (
        not title_a
        or
        not title_b
        or
        title_a != title_b
    ):
        return {
            "duplicate": False,
            "confidence": "low",
            "reason": "different_title",
            "distance_km": None,
        }

    coord_a = get_coordinates(a)
    coord_b = get_coordinates(b)

    if (
        coord_a is None
        or
        coord_b is None
    ):
        return {
            "duplicate": True,
            "confidence": "medium",
            "reason": "same_title_province_no_coordinates",
            "distance_km": None,
        }

    distance = haversine_km(
        coord_a[0],
        coord_a[1],
        coord_b[0],
        coord_b[1],
    )

    return {
        "duplicate":
            distance
            <= coordinate_threshold_km,
        "confidence":
            "high"
            if distance
            <= coordinate_threshold_km
            else "low",
        "reason":
            "same_title_nearby"
            if distance
            <= coordinate_threshold_km
            else "same_title_far_apart",
        "distance_km":
            distance,
    }


def find_duplicates(
    candidate,
    existing_records,
):
    matches = []

    for existing in (
        existing_records
        or []
    ):
        result = compare_identity(
            candidate,
            existing,
        )

        if result["duplicate"]:
            matches.append(
                {
                    "existing":
                        existing,
                    "decision":
                        result,
                }
            )

    return matches
