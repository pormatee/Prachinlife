"""Persistence boundary for Place Platform V2.

Concrete storage (memory, SQLite, PostgreSQL/PostGIS, remote service) must
implement these contracts. Domain and discovery code must not depend on a
specific database driver.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from .models import CanonicalPlace, PlaceEvidence


class PlaceRepository(Protocol):
    def get_place(self, place_id: str) -> CanonicalPlace | None: ...

    def save_place(self, place: CanonicalPlace) -> None: ...

    def add_evidence(self, evidence: PlaceEvidence) -> None: ...

    def list_evidence(self, place_id: str) -> Sequence[PlaceEvidence]: ...


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
