"""Read-only bridge from the consumer-safe published read model to MSB V1.

This module deliberately consumes PublishedPlaceView, not CanonicalPlace or raw
PlaceEvidence. Missing decision-time facts remain missing/unknown rather than
being invented. SQLite access uses URI mode=ro and SELECT only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import json
import sqlite3
from typing import Iterable

from .contracts import GeoPoint
from .master_super_brain_v1 import DecisionCandidate, EvidenceItem
from .models import PlaceLifecycle
from .publication import PublishedPlaceView


def _normal(value: str) -> str:
    return " ".join(str(value).casefold().split())


def _distance_km(a: GeoPoint, b: GeoPoint) -> float | None:
    if a is None or b is None:
        return None
    earth = 6371.0088
    lat1, lon1, lat2, lon2 = map(
        radians, (a.latitude, a.longitude, b.latitude, b.longitude)
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    x = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * earth * asin(sqrt(x))


def _vegetarian_from_categories(categories: tuple[str, ...]) -> bool | None:
    markers = ("vegetarian", "vegan", "jay", "เจ", "มังสวิรัติ")
    normalized = tuple(_normal(x) for x in categories)
    if any(any(marker in category for marker in markers) for category in normalized):
        return True
    # Absence of a vegetarian label is not proof of non-vegetarian.
    return None


def _published_evidence(
    field: str,
    value,
    place: PublishedPlaceView,
    *,
    status: str = "verified",
    confidence: float = 1.0,
    source_suffix: str = "",
) -> EvidenceItem:
    suffix = f":{source_suffix}" if source_suffix else ""
    return EvidenceItem(
        field=field,
        value=value,
        status=status,
        confidence=confidence,
        observed_at=place.published_at.isoformat(),
        source_ref=f"published:{place.publication_policy_version}:{place.place_id}{suffix}",
    )


def published_place_to_decision_candidate(
    place: PublishedPlaceView,
    *,
    origin: GeoPoint | None = None,
    distance_scale_km: float = 20.0,
) -> DecisionCandidate:
    """Map one already-published place into a DecisionCandidate.

    Publication-safe fields are carried as verified publication facts. Derived
    values are marked supported, not verified. Dynamic facts such as open_now,
    in_stock, price and availability are intentionally absent when the read
    model does not provide them.
    """
    if distance_scale_km <= 0:
        raise ValueError("distance_scale_km must be greater than zero")

    attrs = {
        "name": place.name,
        "province": place.province,
        "categories": tuple(place.categories),
        "lifecycle": place.lifecycle.value,
        "address_text": place.address_text,
        "phone": place.phone,
        "website": place.website,
        "publication_policy_version": place.publication_policy_version,
        "published_at": place.published_at.isoformat(),
        "latitude": (place.location.latitude if place.location is not None else None),
        "longitude": (place.location.longitude if place.location is not None else None),
    }
    evidence = [
        _published_evidence("name", place.name, place),
        _published_evidence("province", place.province, place),
        _published_evidence("categories", tuple(place.categories), place),
        _published_evidence("lifecycle", place.lifecycle.value, place),
        _published_evidence(
            "location",
            (((place.location.latitude, place.location.longitude) if place.location is not None else None) if place.location is not None else None),
            place,
        ),
    ]

    vegetarian = _vegetarian_from_categories(tuple(place.categories))
    if vegetarian is True:
        attrs["vegetarian"] = True
        evidence.append(
            _published_evidence(
                "vegetarian",
                True,
                place,
                status="supported",
                confidence=0.85,
                source_suffix="derived-from-categories",
            )
        )

    if origin is not None:
        km = _distance_km(origin, place.location)
        norm = None if km is None else max(0.0, min(1.0, km / distance_scale_km))
        attrs["distance_km"] = km
        attrs["distance_norm"] = norm
        evidence.append(
            _published_evidence(
                "distance_norm",
                norm,
                place,
                status="supported",
                confidence=1.0,
                source_suffix="derived-geometry",
            )
        )

    return DecisionCandidate(
        candidate_id=place.place_id,
        entity_type="place",
        attributes=attrs,
        evidence=tuple(evidence),
        is_sponsored=False,
        promotion_ref=None,
    )


@dataclass(frozen=True)
class PublishedDecisionQuery:
    province: str | None = None
    categories: tuple[str, ...] = ()
    origin: GeoPoint | None = None
    radius_km: float | None = None
    limit: int = 50
    distance_scale_km: float = 20.0

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be greater than zero")
        if self.radius_km is not None and self.radius_km <= 0:
            raise ValueError("radius_km must be greater than zero")
        if self.radius_km is not None and self.origin is None:
            raise ValueError("origin is required when radius_km is set")


class ReadOnlyPublishedSQLiteSource:
    """Minimal read-only source over the existing published_places table."""

    def __init__(self, database: str | Path) -> None:
        path = Path(database).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        self.database = path

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self.database.as_posix()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        return con

    def table_exists(self) -> bool:
        with self._connect() as con:
            row = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='published_places'"
            ).fetchone()
        return row is not None

    def count(self) -> int:
        if not self.table_exists():
            return 0
        with self._connect() as con:
            row = con.execute("SELECT COUNT(*) AS n FROM published_places").fetchone()
        return int(row["n"])

    def list_views(self, query: PublishedDecisionQuery = PublishedDecisionQuery()) -> tuple[PublishedPlaceView, ...]:
        if not self.table_exists():
            return ()
        with self._connect() as con:
            rows = con.execute("SELECT * FROM published_places").fetchall()

        requested = {_normal(x) for x in query.categories}
        result: list[tuple[float, PublishedPlaceView]] = []
        for row in rows:
            if query.province is not None and _normal(row["province"]) != _normal(query.province):
                continue
            categories = tuple(json.loads(row["categories_json"]))
            if requested and not requested.intersection(_normal(x) for x in categories):
                continue
            view = PublishedPlaceView(
                place_id=row["place_id"],
                name=row["name"],
                location=GeoPoint(float(row["latitude"]), float(row["longitude"])),
                province=row["province"],
                categories=categories,
                lifecycle=PlaceLifecycle(row["lifecycle"]),
                address_text=row["address_text"],
                phone=row["phone"],
                website=row["website"],
                publication_policy_version=row["publication_policy_version"],
                published_at=datetime.fromisoformat(row["published_at"]),
            )
            distance = 0.0
            if query.origin is not None:
                distance = _distance_km(query.origin, view.location)
                if query.radius_km is not None and distance > query.radius_km:
                    continue
            result.append((distance, view))

        result.sort(key=lambda x: (x[0], _normal(x[1].name), x[1].place_id))
        return tuple(view for _, view in result[: query.limit])

    def decision_candidates(
        self, query: PublishedDecisionQuery = PublishedDecisionQuery()
    ) -> tuple[DecisionCandidate, ...]:
        return tuple(
            published_place_to_decision_candidate(
                view,
                origin=query.origin,
                distance_scale_km=query.distance_scale_km,
            )
            for view in self.list_views(query)
        )
