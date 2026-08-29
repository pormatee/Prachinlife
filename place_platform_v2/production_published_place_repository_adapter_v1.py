from __future__ import annotations
from pathlib import Path
from typing import Any

from .production_published_place_consumer_v1 import ProductionPublishedPlaceConsumerV1


class ProductionPublishedPlaceRepositoryAdapterV1:
    """Narrow read-only adapter exposing the repository-shaped methods used by
    the existing end-to-end real decision flow. It delegates all reads to the
    frozen production persisted-projection consumer.
    """

    def __init__(self, repo_root: str | Path, projection_path: str | Path | None = None):
        self.consumer = ProductionPublishedPlaceConsumerV1(repo_root, projection_path)

    def get_published(self, place_id: str):
        return self.consumer.get_published(place_id)

    def search_text(self, query):
        # Existing repository contract uses a query object. Preserve it exactly.
        return self.consumer.repository.search_text(query)

    def search_nearby(self, query):
        return self.consumer.repository.search_nearby(query)
