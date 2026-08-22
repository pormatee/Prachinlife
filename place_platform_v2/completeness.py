from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


MISSING_DETAIL_FIELDS = (
    "district",
    "subdistrict",
    "area",
    "opening_hours",
    "phone",
    "website",
    "real_image",
    "description",
)


def _present(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


def _real_image(place: dict[str, Any]) -> Any:
    metadata = place.get("metadata") if isinstance(place.get("metadata"), dict) else {}
    for key in ("image_url", "image", "photo_url", "photo", "thumbnail_url", "thumbnail"):
        if _present(place.get(key)):
            return place.get(key)
        if _present(metadata.get(key)):
            return metadata.get(key)
    return None


def _field_value(place: dict[str, Any], field: str) -> Any:
    metadata = place.get("metadata") if isinstance(place.get("metadata"), dict) else {}
    location = place.get("location") if isinstance(place.get("location"), dict) else {}
    if field == "real_image":
        return _real_image(place)
    if field in ("district", "subdistrict", "area"):
        return place.get(field) or location.get(field)
    if field == "opening_hours":
        return metadata.get("opening_hours") or place.get("opening_hours") or place.get("hours")
    if field == "description":
        return metadata.get("description") or place.get("description") or place.get("summary")
    if field in ("phone", "website"):
        contact = metadata.get("contact") if isinstance(metadata.get("contact"), dict) else {}
        return contact.get(field) or metadata.get(field) or place.get(field)
    return place.get(field)


def audit_places(places: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [p for p in places if isinstance(p, dict)]
    total = len(rows)
    fields: dict[str, dict[str, Any]] = {}

    for field in MISSING_DETAIL_FIELDS:
        present_count = sum(1 for place in rows if _present(_field_value(place, field)))
        missing_count = total - present_count
        fields[field] = {
            "present": present_count,
            "missing": missing_count,
            "coverage_percent": round((present_count / total * 100.0) if total else 0.0, 1),
        }

    required_core = {
        "name": sum(1 for p in rows if _present(p.get("name") or p.get("title"))),
        "coordinates": sum(
            1
            for p in rows
            if _present(p.get("latitude")) and _present(p.get("longitude"))
        ),
        "province": sum(1 for p in rows if _present(p.get("province"))),
        "categories": sum(1 for p in rows if _present(p.get("categories"))),
        "source_name": sum(1 for p in rows if _present(p.get("source_name"))),
        "source_url": sum(1 for p in rows if _present(p.get("source_url"))),
    }

    priorities = sorted(
        (
            {
                "field": field,
                "missing": stats["missing"],
                "coverage_percent": stats["coverage_percent"],
                "priority": (
                    "critical"
                    if field in {"district", "subdistrict", "area", "real_image"}
                    else "high"
                    if field in {"opening_hours", "phone", "website"}
                    else "medium"
                ),
            }
            for field, stats in fields.items()
        ),
        key=lambda item: (
            {"critical": 0, "high": 1, "medium": 2}[item["priority"]],
            -item["missing"],
            item["field"],
        ),
    )

    return {
        "place_count": total,
        "core": required_core,
        "detail_fields": fields,
        "admin_priority": priorities,
    }
