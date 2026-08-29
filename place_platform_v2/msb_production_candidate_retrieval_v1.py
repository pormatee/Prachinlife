from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .production_published_place_consumer_v1 import ProductionPublishedPlaceConsumerV1


@dataclass(frozen=True)
class ProductionCandidateFactV1:
    place_id: str
    name: str
    province: str | None
    categories: tuple[str, ...]
    latitude: float | None
    longitude: float | None
    address: str | None
    published_at: object | None
    policy_version: str | None
    source_kind: str = "authoritative_persisted_projection"


@dataclass(frozen=True)
class ProductionCandidateQueryV1:
    text: str = ""
    province: str | None = None
    categories: tuple[str, ...] = ()
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float | None = None
    limit: int = 50


@dataclass(frozen=True)
class ProductionCandidateResultV1:
    candidates: tuple[ProductionCandidateFactV1, ...]
    retrieval_mode: str
    authoritative_source: str = "decision_published_places_v1"
    missing_coordinate_count: int = 0


class MSBProductionCandidateRetrievalV1:
    """Read-only bridge from authoritative published projection to MSB/DQE candidate facts.

    This module intentionally does not rank, infer missing facts, change trust policy,
    approve/publish places, or write canonical data.
    """

    def __init__(
        self,
        repo_root: str | Path,
        projection_path: str | Path | None = None,
    ) -> None:
        self.consumer = ProductionPublishedPlaceConsumerV1(
            repo_root=repo_root,
            projection_path=projection_path,
        )

    @staticmethod
    def _fact(view) -> ProductionCandidateFactV1:
        location = getattr(view, "location", None)
        lat = getattr(location, "latitude", None) if location is not None else None
        lon = getattr(location, "longitude", None) if location is not None else None
        return ProductionCandidateFactV1(
            place_id=str(view.place_id),
            name=str(view.name),
            province=getattr(view, "province", None),
            categories=tuple(getattr(view, "categories", ()) or ()),
            latitude=lat,
            longitude=lon,
            address=getattr(view, "address", None),
            published_at=getattr(view, "published_at", None),
            policy_version=getattr(view, "policy_version", None),
        )

    def retrieve(self, query: ProductionCandidateQueryV1) -> ProductionCandidateResultV1:
        if query.limit <= 0:
            raise ValueError("limit must be > 0")

        use_nearby = (
            query.latitude is not None
            or query.longitude is not None
            or query.radius_km is not None
        )

        if use_nearby:
            if (
                query.latitude is None
                or query.longitude is None
                or query.radius_km is None
            ):
                raise ValueError(
                    "latitude, longitude, and radius_km must be supplied together"
                )
            nearby = self.consumer.nearby(
                latitude=float(query.latitude),
                longitude=float(query.longitude),
                radius_km=float(query.radius_km),
                province=query.province,
                categories=query.categories,
                limit=query.limit,
            )
            # PublishedNearbyResult wraps PublishedPlaceView as `.place`.
            views = [x.place for x in nearby]
            mode = "nearby"
        elif query.text.strip():
            views = list(
                self.consumer.search_text(
                    query.text,
                    province=query.province,
                    categories=query.categories,
                    limit=query.limit,
                )
            )
            mode = "text"
        else:
            views = list(
                self.consumer.list_places(
                    province=query.province,
                    categories=query.categories,
                    limit=query.limit,
                )
            )
            mode = "filter"

        facts = tuple(self._fact(x) for x in views)
        return ProductionCandidateResultV1(
            candidates=facts,
            retrieval_mode=mode,
            missing_coordinate_count=sum(
                1 for x in facts if x.latitude is None or x.longitude is None
            ),
        )
