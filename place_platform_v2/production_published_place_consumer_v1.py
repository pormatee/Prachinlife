from __future__ import annotations

from pathlib import Path

from .persisted_published_projection_v1 import SQLitePublishedPlaceRepositoryV1
from .read_model import PublishedNearbyQuery, PublishedTextQuery
from .sqlite_store import GeoPoint

DEFAULT_PROJECTION_REL = Path("data/v2/decision_published_places_v1.sqlite3")


class ProductionPublishedPlaceConsumerV1:
    """Read-only consumer facade over the authoritative persisted projection."""

    def __init__(self, repo_root: str | Path, projection_path: str | Path | None = None):
        self.repo_root = Path(repo_root)
        self.projection_path = (
            Path(projection_path)
            if projection_path is not None
            else self.repo_root / DEFAULT_PROJECTION_REL
        )
        if not self.projection_path.exists():
            raise FileNotFoundError(
                f"authoritative persisted projection is not available: {self.projection_path}"
            )
        self.repository = SQLitePublishedPlaceRepositoryV1(self.projection_path)

    def get_published(self, place_id: str):
        return self.repository.get_published(place_id)

    def list_places(
        self,
        *,
        province: str | None = None,
        categories=(),
        limit: int = 100000,
    ):
        return self.repository.search_text(PublishedTextQuery(
            text="",
            province=province,
            categories=tuple(categories or ()),
            limit=int(limit),
        ))

    def search_text(
        self,
        text: str,
        *,
        province: str | None = None,
        categories=(),
        limit: int = 50,
    ):
        return self.repository.search_text(PublishedTextQuery(
            text=text,
            province=province,
            categories=tuple(categories or ()),
            limit=int(limit),
        ))

    def nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float,
        province: str | None = None,
        categories=(),
        limit: int = 50,
    ):
        return self.repository.search_nearby(PublishedNearbyQuery(
            origin=GeoPoint(float(latitude), float(longitude)),
            radius_km=float(radius_km),
            categories=tuple(categories or ()),
            province=province,
            limit=int(limit),
        ))


def open_production_published_place_consumer_v1(
    repo_root: str | Path,
    projection_path: str | Path | None = None,
) -> ProductionPublishedPlaceConsumerV1:
    return ProductionPublishedPlaceConsumerV1(repo_root, projection_path)
