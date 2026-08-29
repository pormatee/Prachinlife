"""Persisted Published Projection V1.

Storage boundary:
Controlled Publication -> persisted projection -> read-only repository -> Brain.

This module deliberately separates the writable projection publisher from the
read-only repository consumed by decision flows.
"""
from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from enum import Enum
import importlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .publication import PublishedPlaceView
from .read_model import PublishedNearbyQuery, PublishedNearbyResult, PublishedTextQuery


_TABLE = "decision_published_places_v1"
_SCHEMA_VERSION = "PERSISTED-PUBLISHED-PROJECTION-V1"


def _qualified_name(obj: Any) -> str:
    cls = obj if isinstance(obj, type) else type(obj)
    return f"{cls.__module__}:{cls.__qualname__}"


def _resolve_class(name: str) -> type:
    module_name, qualname = name.split(":", 1)
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    if not isinstance(obj, type):
        raise TypeError(f"not a class: {name}")
    return obj


def _encode(value: Any) -> Any:
    if is_dataclass(value):
        return {
            "__kind__": "dataclass",
            "__type__": _qualified_name(value),
            "fields": {f.name: _encode(getattr(value, f.name)) for f in fields(value)},
        }
    if isinstance(value, Enum):
        return {"__kind__": "enum", "__type__": _qualified_name(value), "value": _encode(value.value)}
    if isinstance(value, tuple):
        return {"__kind__": "tuple", "items": [_encode(v) for v in value]}
    if isinstance(value, set):
        return {"__kind__": "set", "items": [_encode(v) for v in sorted(value, key=repr)]}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, datetime):
        return {"__kind__": "datetime", "value": value.isoformat()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported projection value type: {type(value)!r}")


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    kind = value.get("__kind__")
    if kind == "dataclass":
        cls = _resolve_class(value["__type__"])
        kwargs = {k: _decode(v) for k, v in value["fields"].items()}
        return cls(**kwargs)
    if kind == "enum":
        cls = _resolve_class(value["__type__"])
        return cls(_decode(value["value"]))
    if kind == "tuple":
        return tuple(_decode(v) for v in value["items"])
    if kind == "set":
        return set(_decode(v) for v in value["items"])
    if kind == "datetime":
        return datetime.fromisoformat(value["value"])
    return {k: _decode(v) for k, v in value.items()}


def _serialize(view: PublishedPlaceView) -> str:
    if not isinstance(view, PublishedPlaceView):
        raise TypeError("projection accepts PublishedPlaceView only")
    return json.dumps(_encode(view), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _deserialize(payload: str) -> PublishedPlaceView:
    obj = _decode(json.loads(payload))
    if not isinstance(obj, PublishedPlaceView):
        raise TypeError("persisted payload is not PublishedPlaceView")
    return obj


def _value(view: Any, *names: str) -> Any:
    for name in names:
        if hasattr(view, name):
            return getattr(view, name)
    return None


def _categories(view: Any) -> tuple[str, ...]:
    raw = _value(view, "categories", "category_ids", "category")
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    try:
        return tuple(str(v) for v in raw)
    except TypeError:
        return (str(raw),)


def _coord(view: Any) -> tuple[float, float] | None:
    lat = _value(view, "latitude", "lat")
    lon = _value(view, "longitude", "lon", "lng")
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    c = _value(view, "coordinate", "coordinates", "location")
    if c is None:
        return None
    lat = _value(c, "latitude", "lat")
    lon = _value(c, "longitude", "lon", "lng")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _normal(value: Any) -> str:
    """Consumer-read-model compatible lightweight normalization."""
    return " ".join(str(value or "").casefold().split())


def _matches_categories(view: Any, requested: Iterable[str]) -> bool:
    wanted = {_normal(v) for v in (requested or ()) if _normal(v)}
    if not wanted:
        return True
    actual = {_normal(v) for v in _categories(view) if _normal(v)}
    return bool(wanted & actual)


class PersistedPublishedProjectionWriterV1:
    """Writable side. Intended for controlled-publication code only."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def ensure_schema(self) -> None:
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    place_id TEXT PRIMARY KEY,
                    province TEXT,
                    categories_json TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    payload_json TEXT NOT NULL,
                    projection_schema_version TEXT NOT NULL
                )
            """)
            con.execute(f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_province ON {_TABLE}(province)")
            con.commit()
        finally:
            con.close()

    def upsert(self, view: PublishedPlaceView) -> None:
        self.ensure_schema()
        place_id = str(_value(view, "place_id", "id") or "")
        if not place_id:
            raise ValueError("PublishedPlaceView must expose place_id")
        province = _value(view, "province")
        categories = _categories(view)
        coord = _coord(view)
        lat, lon = coord if coord else (None, None)
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                f"""INSERT INTO {_TABLE}
                    (place_id, province, categories_json, latitude, longitude, payload_json, projection_schema_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(place_id) DO UPDATE SET
                      province=excluded.province,
                      categories_json=excluded.categories_json,
                      latitude=excluded.latitude,
                      longitude=excluded.longitude,
                      payload_json=excluded.payload_json,
                      projection_schema_version=excluded.projection_schema_version
                """,
                (place_id, province, json.dumps(categories, ensure_ascii=False), lat, lon,
                 _serialize(view), _SCHEMA_VERSION),
            )
            con.commit()
        finally:
            con.close()

    def remove(self, place_id: str) -> None:
        self.ensure_schema()
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(f"DELETE FROM {_TABLE} WHERE place_id=?", (str(place_id),))
            con.commit()
        finally:
            con.close()


class SQLitePublishedPlaceRepositoryV1:
    """Read-only adapter used by the Brain-facing decision flow."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{Path(self.db_path).resolve()}?mode=ro", uri=True)

    def _all(self) -> list[PublishedPlaceView]:
        con = self._connect()
        try:
            rows = con.execute(
                f"SELECT payload_json FROM {_TABLE} WHERE projection_schema_version=? ORDER BY place_id",
                (_SCHEMA_VERSION,),
            ).fetchall()
        finally:
            con.close()
        return [_deserialize(row[0]) for row in rows]

    def get_published(self, place_id: str) -> PublishedPlaceView | None:
        con = self._connect()
        try:
            row = con.execute(
                f"SELECT payload_json FROM {_TABLE} WHERE place_id=? AND projection_schema_version=?",
                (str(place_id), _SCHEMA_VERSION),
            ).fetchone()
        finally:
            con.close()
        return None if row is None else _deserialize(row[0])

    def search_text(self, query: PublishedTextQuery) -> tuple[PublishedPlaceView, ...]:
        needle = _normal(getattr(query, "text", ""))
        province = getattr(query, "province", None)
        limit = int(getattr(query, "limit", 50))
        requested_categories = getattr(query, "categories", ()) or ()

        matches: list[PublishedPlaceView] = []
        for view in self._all():
            if province is not None and _normal(_value(view, "province")) != _normal(province):
                continue
            if not _matches_categories(view, requested_categories):
                continue

            haystack = _normal(" ".join(
                str(value) for value in (
                    _value(view, "canonical_name", "name", "display_name") or "",
                    _value(view, "address_text", "address") or "",
                    _value(view, "province") or "",
                    " ".join(_categories(view)),
                ) if value
            ))
            if needle and needle not in haystack:
                continue
            matches.append(view)

        matches.sort(key=lambda view: (
            _normal(_value(view, "canonical_name", "name", "display_name") or ""),
            _normal(_value(view, "address_text", "address") or ""),
            _normal(_value(view, "province") or ""),
            tuple(sorted(_normal(v) for v in _categories(view))),
            _coord(view) or (float("inf"), float("inf")),
        ))
        return tuple(matches[:limit])

    def search_nearby(self, query: PublishedNearbyQuery) -> tuple[PublishedNearbyResult, ...]:
        origin = getattr(query, "origin")
        if hasattr(origin, "latitude"):
            origin_pair = (float(origin.latitude), float(origin.longitude))
        elif hasattr(origin, "lat"):
            origin_pair = (
                float(origin.lat),
                float(getattr(origin, "lon", getattr(origin, "lng"))),
            )
        else:
            origin_pair = (float(origin[0]), float(origin[1]))

        radius = float(getattr(query, "radius_km"))
        province = getattr(query, "province", None)
        requested_categories = getattr(query, "categories", ()) or ()
        limit = int(getattr(query, "limit", 50))

        matches: list[PublishedNearbyResult] = []
        for view in self._all():
            if province is not None and _normal(_value(view, "province")) != _normal(province):
                continue
            if not _matches_categories(view, requested_categories):
                continue

            coordinate = _coord(view)
            if coordinate is None:
                continue
            distance = _haversine_km(origin_pair, coordinate)
            if distance <= radius:
                matches.append(PublishedNearbyResult(view, distance))

        matches.sort(key=lambda item: (
            item.distance_km,
            _normal(_value(item.place, "canonical_name", "name", "display_name") or ""),
            _normal(_value(item.place, "address_text", "address") or ""),
            _normal(_value(item.place, "province") or ""),
            tuple(sorted(_normal(v) for v in _categories(item.place))),
            _coord(item.place) or (float("inf"), float("inf")),
        ))
        return tuple(matches[:limit])
