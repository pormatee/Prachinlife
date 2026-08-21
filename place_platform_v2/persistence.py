"""Storage-neutral persistence schema and capability contract for Place Platform V2.

This module describes what a concrete database must support. It deliberately
contains no SQL driver, connection string, or vendor-specific migration code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import GeoPoint


SCHEMA_VERSION = "2.0-packet3"


class ColumnRole(str, Enum):
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    VALUE = "value"
    PROVENANCE = "provenance"
    GEO = "geo"
    TIMESTAMP = "timestamp"


@dataclass(frozen=True)
class SchemaColumn:
    name: str
    role: ColumnRole
    required: bool = True


@dataclass(frozen=True)
class SchemaTable:
    name: str
    columns: tuple[SchemaColumn, ...]
    append_only: bool = False


@dataclass(frozen=True)
class PersistenceSchema:
    version: str
    tables: tuple[SchemaTable, ...]

    def table(self, name: str) -> SchemaTable:
        for table in self.tables:
            if table.name == name:
                return table
        raise KeyError(name)


@dataclass(frozen=True)
class DatabaseCapabilities:
    geographic_point_storage: bool = True
    radius_search: bool = True
    distance_ordering: bool = True
    transactional_writes: bool = True
    append_only_evidence: bool = True
    append_only_history: bool = True

    def supports_near_me(self) -> bool:
        return (
            self.geographic_point_storage
            and self.radius_search
            and self.distance_ordering
        )


@dataclass(frozen=True)
class NearbyPlaceQuery:
    origin: GeoPoint
    radius_km: float
    categories: tuple[str, ...] = ()
    include_non_active: bool = False
    limit: int = 50

    def __post_init__(self) -> None:
        if self.radius_km <= 0:
            raise ValueError("radius_km must be greater than zero")
        if self.limit <= 0:
            raise ValueError("limit must be greater than zero")
        if any(not item.strip() for item in self.categories):
            raise ValueError("categories must not contain blank values")


@dataclass(frozen=True)
class NearbyPlaceResult:
    place_id: str
    distance_km: float

    def __post_init__(self) -> None:
        if self.distance_km < 0:
            raise ValueError("distance_km cannot be negative")


PLACE_SCHEMA_V2 = PersistenceSchema(
    version=SCHEMA_VERSION,
    tables=(
        SchemaTable(
            name="places",
            columns=(
                SchemaColumn("place_id", ColumnRole.PRIMARY_KEY),
                SchemaColumn("canonical_name", ColumnRole.VALUE),
                SchemaColumn("latitude", ColumnRole.GEO, required=False),
                SchemaColumn("longitude", ColumnRole.GEO, required=False),
                SchemaColumn("address_text", ColumnRole.VALUE, required=False),
                SchemaColumn("province", ColumnRole.VALUE, required=False),
                SchemaColumn("categories", ColumnRole.VALUE),
                SchemaColumn("phone", ColumnRole.VALUE, required=False),
                SchemaColumn("website", ColumnRole.VALUE, required=False),
                SchemaColumn("lifecycle", ColumnRole.VALUE),
                SchemaColumn("created_at", ColumnRole.TIMESTAMP),
                SchemaColumn("updated_at", ColumnRole.TIMESTAMP),
            ),
        ),
        SchemaTable(
            name="place_evidence",
            columns=(
                SchemaColumn("evidence_id", ColumnRole.PRIMARY_KEY),
                SchemaColumn("place_id", ColumnRole.FOREIGN_KEY),
                SchemaColumn("source_type", ColumnRole.PROVENANCE),
                SchemaColumn("source_name", ColumnRole.PROVENANCE),
                SchemaColumn("source_record_id", ColumnRole.PROVENANCE, required=False),
                SchemaColumn("source_url", ColumnRole.PROVENANCE, required=False),
                SchemaColumn("kind", ColumnRole.VALUE),
                SchemaColumn("field_name", ColumnRole.VALUE),
                SchemaColumn("value", ColumnRole.VALUE),
                SchemaColumn("status", ColumnRole.VALUE),
                SchemaColumn("observed_at", ColumnRole.TIMESTAMP),
            ),
            append_only=True,
        ),
        SchemaTable(
            name="place_revisions",
            columns=(
                SchemaColumn("revision_id", ColumnRole.PRIMARY_KEY),
                SchemaColumn("place_id", ColumnRole.FOREIGN_KEY),
                SchemaColumn("change_type", ColumnRole.VALUE),
                SchemaColumn("changed_fields", ColumnRole.VALUE),
                SchemaColumn("reason", ColumnRole.PROVENANCE, required=False),
                SchemaColumn("evidence_ids", ColumnRole.PROVENANCE),
                SchemaColumn("created_at", ColumnRole.TIMESTAMP),
            ),
            append_only=True,
        ),
    ),
)
