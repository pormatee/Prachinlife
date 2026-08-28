from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .persisted_published_projection_v1 import PersistedPublishedProjectionWriterV1
from .read_model import PublishedPlaceView
from .sqlite_store import GeoPoint, PlaceLifecycle

BUNDLE_FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)
SCHEMA_VERSION = "CONTROLLED-PUBLICATION-BUNDLE-ADAPTER-V1"


def _records(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ("places", "items", "data", "results"):
            value = obj.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _categories(record: dict[str, Any], filename: str) -> tuple[str, ...]:
    raw = record.get("categories")
    out: list[str] = []
    if isinstance(raw, str):
        out.append(raw)
    elif isinstance(raw, (list, tuple)):
        out.extend(str(x) for x in raw if x not in (None, ""))

    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        label = metadata.get("category_label")
        if label:
            out.append(str(label))

    if not out:
        fallback = {
            "prachinlife_index.json": "eat",
            "vegetarian_index.json": "vegetarian",
            "go_index.json": "go",
            "service_index.json": "service",
        }.get(filename)
        if fallback:
            out.append(fallback)

    seen = set()
    clean = []
    for value in out:
        key = " ".join(value.casefold().split())
        if key and key not in seen:
            seen.add(key)
            clean.append(value.strip())
    return tuple(clean)


def _location(record: dict[str, Any]) -> tuple[float | None, float | None, str | None, str | None]:
    loc = record.get("location")
    loc = loc if isinstance(loc, dict) else {}

    lat = _float(record.get("latitude"))
    if lat is None:
        lat = _float(loc.get("latitude"))
    lon = _float(record.get("longitude"))
    if lon is None:
        lon = _float(record.get("lng"))
    if lon is None:
        lon = _float(loc.get("longitude"))

    province = _text(record.get("province")) or _text(loc.get("province"))
    address = _text(record.get("address")) or _text(record.get("address_text"))
    if address is None:
        district = _text(loc.get("district"))
        subdistrict = _text(loc.get("subdistrict"))
        address = " ".join(x for x in (subdistrict, district, province) if x) or None
    return lat, lon, province, address


def _identity(record: dict[str, Any]) -> str | None:
    metadata = record.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    # Public record id remains primary because it is the bundle identity contract.
    return _text(record.get("place_id")) or _text(record.get("id")) or _text(metadata.get("v2_place_id"))


def _name(record: dict[str, Any]) -> str | None:
    return (
        _text(record.get("name"))
        or _text(record.get("title"))
        or _text(record.get("canonical_name"))
    )


def _published_at(record: dict[str, Any]) -> datetime:
    for key in ("published_at", "collected_at", "updated_at"):
        value = record.get(key)
        if not value:
            continue
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def record_to_view(record: dict[str, Any], filename: str) -> PublishedPlaceView | None:
    place_id = _identity(record)
    name = _name(record)
    lat, lon, province, address = _location(record)
    if not place_id or not name or not province:
        return None

    metadata = record.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    policy = (
        _text(record.get("publication_policy_version"))
        or _text(metadata.get("v2_policy_version"))
        or SCHEMA_VERSION
    )
    lifecycle_raw = (_text(record.get("lifecycle")) or "active").upper()
    try:
        lifecycle = PlaceLifecycle[lifecycle_raw]
    except Exception:
        lifecycle = PlaceLifecycle.ACTIVE

    location = GeoPoint(lat, lon) if lat is not None and lon is not None else None

    return PublishedPlaceView(
        place_id=place_id,
        name=name,
        location=location,
        province=province,
        categories=_categories(record, filename),
        lifecycle=lifecycle,
        address_text=address,
        phone=_text(record.get("phone")) or _text(metadata.get("phone")),
        website=_text(record.get("website")) or _text(metadata.get("website")),
        publication_policy_version=policy,
        published_at=_published_at(record),
    )


def load_bundle_views(repo_root: str | Path) -> tuple[tuple[PublishedPlaceView, ...], dict[str, Any]]:
    root = Path(repo_root)
    selected: dict[str, PublishedPlaceView] = {}
    source_files: dict[str, str] = {}
    total_records = 0
    rejected = 0
    duplicate_ids: list[str] = []

    for filename in BUNDLE_FILES:
        path = root / filename
        obj = json.loads(path.read_text(encoding="utf-8"))
        for record in _records(obj):
            total_records += 1
            view = record_to_view(record, filename)
            if view is None:
                rejected += 1
                continue
            if view.place_id in selected:
                duplicate_ids.append(view.place_id)
                current = selected[view.place_id]
                merged_categories = []
                seen_categories = set()
                for category in tuple(current.categories) + tuple(view.categories):
                    key = " ".join(str(category).casefold().split())
                    if key and key not in seen_categories:
                        seen_categories.add(key)
                        merged_categories.append(str(category))
                selected[view.place_id] = PublishedPlaceView(
                    place_id=current.place_id,
                    name=current.name,
                    location=current.location,
                    province=current.province,
                    categories=tuple(merged_categories),
                    lifecycle=current.lifecycle,
                    address_text=current.address_text,
                    phone=current.phone,
                    website=current.website,
                    publication_policy_version=current.publication_policy_version,
                    published_at=current.published_at,
                )
                continue
            selected[view.place_id] = view
            source_files[view.place_id] = filename

    views = tuple(sorted(selected.values(), key=lambda x: x.place_id))
    report = {
        "status": "PASS",
        "bundle_files": list(BUNDLE_FILES),
        "total_records": total_records,
        "projection_count": len(views),
        "rejected_record_count": rejected,
        "duplicate_record_count": len(duplicate_ids),
        "duplicate_ids": sorted(set(duplicate_ids)),
        "dedupe_policy": "FIRST_FILE_SCALARS_CATEGORY_UNION_BUNDLE_ORDER",
        "consumer_switched": False,
    }
    return views, report


def build_projection_database(repo_root: str | Path, projection_database: str | Path) -> dict[str, Any]:
    views, report = load_bundle_views(repo_root)
    db = Path(projection_database)
    writer = PersistedPublishedProjectionWriterV1(db)
    for view in views:
        writer.upsert(view)
    out = dict(report)
    out["projection_database"] = str(db)
    return out
