"""Consumer-facing published place read model for Place Platform V2.

Only :class:`PublishedPlaceView` instances may enter this repository. Search
consumers never receive canonical places, evidence, or revisions through this
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Protocol, Sequence

from .contracts import GeoPoint
from .publication import PublishedPlaceView


@dataclass(frozen=True)
class PublishedNearbyQuery:
    origin: GeoPoint
    radius_km: float
    categories: tuple[str, ...] = ()
    province: str | None = None
    limit: int = 50

    def __post_init__(self) -> None:
        if self.radius_km <= 0:
            raise ValueError("radius_km must be greater than zero")
        if self.limit <= 0:
            raise ValueError("limit must be greater than zero")
        if any(not item.strip() for item in self.categories):
            raise ValueError("categories must not contain blank values")
        if self.province is not None and not self.province.strip():
            raise ValueError("province must not be blank")


@dataclass(frozen=True)
class PublishedTextQuery:
    text: str = ""
    categories: tuple[str, ...] = ()
    province: str | None = None
    limit: int = 50

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be greater than zero")
        if any(not item.strip() for item in self.categories):
            raise ValueError("categories must not contain blank values")
        if self.province is not None and not self.province.strip():
            raise ValueError("province must not be blank")


@dataclass(frozen=True)
class PublishedNearbyResult:
    place: PublishedPlaceView
    distance_km: float

    def __post_init__(self) -> None:
        if self.distance_km < 0:
            raise ValueError("distance_km cannot be negative")


class PublishedPlaceRepository(Protocol):
    """Read-model contract exposed to websites, apps, and AI consumers."""

    def upsert_published(self, place: PublishedPlaceView) -> None: ...

    def remove_published(self, place_id: str) -> None: ...

    def get_published(self, place_id: str) -> PublishedPlaceView | None: ...

    def search_nearby(
        self, query: PublishedNearbyQuery
    ) -> Sequence[PublishedNearbyResult]: ...

    def search_text(self, query: PublishedTextQuery) -> Sequence[PublishedPlaceView]: ...


def _distance_km(origin: GeoPoint, target: GeoPoint) -> float:
    earth_radius_km = 6371.0088
    lat1, lon1, lat2, lon2 = map(
        radians,
        (origin.latitude, origin.longitude, target.latitude, target.longitude),
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(value))


def _normal(value: str) -> str:
    return " ".join(value.casefold().split())


def _matches_categories(place: PublishedPlaceView, categories: tuple[str, ...]) -> bool:
    if not categories:
        return True
    requested = {_normal(item) for item in categories}
    available = {_normal(item) for item in place.categories}
    return bool(requested.intersection(available))


def _matches_province(place: PublishedPlaceView, province: str | None) -> bool:
    if province is None:
        return True
    return _normal(place.province) == _normal(province)


class InMemoryPublishedPlaceRepository:
    """Deterministic reference read model used by contract tests only."""

    def __init__(self) -> None:
        self._places: dict[str, PublishedPlaceView] = {}

    def upsert_published(self, place: PublishedPlaceView) -> None:
        self._places[place.place_id] = place

    def remove_published(self, place_id: str) -> None:
        self._places.pop(place_id, None)

    def get_published(self, place_id: str) -> PublishedPlaceView | None:
        return self._places.get(place_id)

    def search_nearby(
        self, query: PublishedNearbyQuery
    ) -> tuple[PublishedNearbyResult, ...]:
        matches: list[PublishedNearbyResult] = []
        for place in self._places.values():
            if not _matches_province(place, query.province):
                continue
            if not _matches_categories(place, query.categories):
                continue
            distance = _distance_km(query.origin, place.location)
            if distance <= query.radius_km:
                matches.append(PublishedNearbyResult(place=place, distance_km=distance))

        matches.sort(key=lambda item: (item.distance_km, item.place.place_id))
        return tuple(matches[: query.limit])

    def search_text(self, query: PublishedTextQuery) -> tuple[PublishedPlaceView, ...]:
        needle = _normal(query.text)
        matches: list[PublishedPlaceView] = []
        for place in self._places.values():
            if not _matches_province(place, query.province):
                continue
            if not _matches_categories(place, query.categories):
                continue

            haystack = _normal(
                " ".join(
                    value
                    for value in (
                        place.name,
                        place.address_text or "",
                        place.province,
                        " ".join(place.categories),
                    )
                    if value
                )
            )
            if needle and needle not in haystack:
                continue
            matches.append(place)

        matches.sort(key=lambda place: (_normal(place.name), place.place_id))
        return tuple(matches[: query.limit])
