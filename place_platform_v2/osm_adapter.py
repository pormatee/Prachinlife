"""OpenStreetMap Discovery V2 adapter.

Transforms already-fetched Overpass elements into the source-neutral
SourcePlaceCandidate contract. Network fetching remains outside this adapter
so tests and ingestion stay deterministic.

This module does not write canonical data, evidence, publication data,
or V1 production files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .contracts import (
    GeoPoint,
    SourcePlaceCandidate,
    SourceRef,
    SourceType,
)


OSM_SOURCE_NAME = "OpenStreetMap"
OSM_BASE_URL = "https://www.openstreetmap.org"


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def osm_record_id(element: dict[str, Any]) -> str:
    element_type = _clean(element.get("type"))
    element_id = element.get("id")

    if element_type not in {"node", "way", "relation"}:
        raise ValueError("OSM element type must be node, way, or relation")

    if element_id is None:
        raise ValueError("OSM element id is required")

    return f"{element_type}/{element_id}"


def _coordinates(
    element: dict[str, Any],
) -> GeoPoint | None:
    lat = element.get("lat")
    lon = element.get("lon")

    if lat is None or lon is None:
        center = element.get("center")
        if isinstance(center, dict):
            lat = center.get("lat")
            lon = center.get("lon")

    if lat is None or lon is None:
        return None

    return GeoPoint(float(lat), float(lon))


def _address(tags: dict[str, Any]) -> str | None:
    parts = (
        _clean(tags.get("addr:housenumber")),
        _clean(tags.get("addr:street")),
        _clean(tags.get("addr:subdistrict"))
        or _clean(tags.get("addr:suburb")),
        _clean(tags.get("addr:district"))
        or _clean(tags.get("addr:city")),
        _clean(tags.get("addr:province")),
        _clean(tags.get("addr:postcode")),
    )
    values = tuple(value for value in parts if value)
    return ", ".join(values) if values else None


def _categories(tags: dict[str, Any]) -> tuple[str, ...]:
    values: set[str] = set()

    amenity = _clean(tags.get("amenity"))
    shop = _clean(tags.get("shop"))
    tourism = _clean(tags.get("tourism"))
    healthcare = _clean(tags.get("healthcare"))

    if amenity:
        values.add(amenity.casefold())

        if amenity in {
            "restaurant",
            "cafe",
            "fast_food",
            "food_court",
            "ice_cream",
        }:
            values.add("eat")

    if shop:
        values.add("shopping")
        values.add(f"shop:{shop.casefold()}")

    if tourism:
        values.add("travel")
        values.add(f"tourism:{tourism.casefold()}")

    if healthcare:
        values.add("service")
        values.add(f"healthcare:{healthcare.casefold()}")

    diet_vegetarian = _clean(tags.get("diet:vegetarian"))
    diet_vegan = _clean(tags.get("diet:vegan"))

    if diet_vegetarian == "yes":
        values.add("vegetarian")

    if diet_vegan == "yes":
        values.add("vegan")
        values.add("vegetarian")

    return tuple(sorted(values))


def element_to_candidate(
    element: dict[str, Any],
    *,
    observed_at: datetime,
) -> SourcePlaceCandidate | None:
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")

    tags = element.get("tags")
    if not isinstance(tags, dict):
        return None

    name = (
        _clean(tags.get("name"))
        or _clean(tags.get("name:th"))
        or _clean(tags.get("name:en"))
    )

    if not name:
        return None

    record_id = osm_record_id(element)

    phone = (
        _clean(tags.get("phone"))
        or _clean(tags.get("contact:phone"))
    )
    website = (
        _clean(tags.get("website"))
        or _clean(tags.get("contact:website"))
    )
    province = (
        _clean(tags.get("addr:province"))
        or _clean(tags.get("province"))
    )

    return SourcePlaceCandidate(
        source=SourceRef(
            source_type=SourceType.OSM,
            source_name=OSM_SOURCE_NAME,
            source_record_id=record_id,
            source_url=f"{OSM_BASE_URL}/{record_id}",
            observed_at=observed_at,
        ),
        name=name,
        location=_coordinates(element),
        address_text=_address(tags),
        province=province,
        categories=_categories(tags),
        phone=phone,
        website=website,
        raw_attributes={
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "tags": dict(tags),
        },
    )


class OSMPlaceAdapterV2:
    """Adapter over a deterministic set of already-fetched OSM elements."""

    source_type = SourceType.OSM

    def __init__(
        self,
        elements: Iterable[dict[str, Any]],
        *,
        observed_at: datetime | None = None,
    ) -> None:
        self._elements = tuple(elements)
        self._observed_at = (
            observed_at
            if observed_at is not None
            else datetime.now(timezone.utc)
        )

        if self._observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")

    def discover(
        self,
        query: str,
    ) -> tuple[SourcePlaceCandidate, ...]:
        if not query.strip():
            raise ValueError("query is required")

        candidates = []

        for element in self._elements:
            candidate = element_to_candidate(
                element,
                observed_at=self._observed_at,
            )
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                item.source.source_record_id or "",
                item.name.casefold(),
            )
        )

        return tuple(candidates)
