"""Persistence boundary for Place Platform V2.

Concrete storage (memory, SQLite, PostgreSQL/PostGIS, remote service) must
implement these contracts. Domain and discovery code must not depend on a
specific database driver.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Protocol, Sequence

from .models import CanonicalPlace, PlaceEvidence, PlaceLifecycle
from .persistence import NearbyPlaceQuery, NearbyPlaceResult


class PlaceRepository(Protocol):
    def get_place(self, place_id: str) -> CanonicalPlace | None: ...

    def save_place(self, place: CanonicalPlace) -> None: ...

    def add_evidence(self, evidence: PlaceEvidence) -> None: ...

    def list_evidence(self, place_id: str) -> Sequence[PlaceEvidence]: ...

    def search_nearby(self, query: NearbyPlaceQuery) -> Sequence[NearbyPlaceResult]: ...


def _distance_km(origin_lat: float, origin_lon: float, lat: float, lon: float) -> float:
    """Deterministic Haversine distance for the reference repository only."""
    earth_radius_km = 6371.0088
    lat1, lon1, lat2, lon2 = map(radians, (origin_lat, origin_lon, lat, lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(value))


class InMemoryPlaceRepository:
    """Reference implementation used only for deterministic contract tests."""

    def __init__(self) -> None:
        self._places: dict[str, CanonicalPlace] = {}
        self._evidence: dict[str, list[PlaceEvidence]] = {}
        self._evidence_ids: set[str] = set()

    def get_place(self, place_id: str) -> CanonicalPlace | None:
        return self._places.get(place_id)

    def save_place(self, place: CanonicalPlace) -> None:
        self._places[place.identity.place_id] = place

    def add_evidence(self, evidence: PlaceEvidence) -> None:
        if evidence.place_id not in self._places:
            raise KeyError("evidence cannot be attached to an unknown place")
        if evidence.evidence_id in self._evidence_ids:
            raise ValueError("duplicate evidence_id")
        self._evidence.setdefault(evidence.place_id, []).append(evidence)
        self._evidence_ids.add(evidence.evidence_id)

    def list_evidence(self, place_id: str) -> tuple[PlaceEvidence, ...]:
        return tuple(self._evidence.get(place_id, ()))

    def search_nearby(self, query: NearbyPlaceQuery) -> tuple[NearbyPlaceResult, ...]:
        matches: list[NearbyPlaceResult] = []
        requested_categories = set(query.categories)

        for place in self._places.values():
            if place.location is None:
                continue
            if not query.include_non_active and place.lifecycle in {
                PlaceLifecycle.INACTIVE,
                PlaceLifecycle.CLOSED,
            }:
                continue
            if requested_categories and not requested_categories.intersection(place.categories):
                continue

            distance = _distance_km(
                query.origin.latitude,
                query.origin.longitude,
                place.location.latitude,
                place.location.longitude,
            )
            if distance <= query.radius_km:
                matches.append(
                    NearbyPlaceResult(
                        place_id=place.identity.place_id,
                        distance_km=distance,
                    )
                )

        matches.sort(key=lambda result: (result.distance_km, result.place_id))
        return tuple(matches[: query.limit])
