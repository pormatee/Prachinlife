"""V1 JSON -> V2 migration/import contract.

The importer is deliberately source-file agnostic and never mutates its input.
It converts legacy JSON-like mappings into normalized V2 candidates, records
stable provenance, supports dry-run reporting, and provides an idempotency key
that storage adapters can persist independently of canonical place IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json

from .contracts import GeoPoint, SourcePlaceCandidate, SourceRef, SourceType
from .ingestion import IngestionObservation, normalize_candidate, build_claims


class MigrationDisposition(str):
    READY = "ready"
    SKIPPED = "skipped"
    INVALID = "invalid"


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _first(record: Mapping[str, Any], names: Sequence[str]) -> Any:
    for name in names:
        if name in record and record[name] not in (None, "", [], {}):
            return record[name]
    return None


def _categories(record: Mapping[str, Any]) -> tuple[str, ...]:
    raw = _first(record, ("categories", "category", "type", "food_type", "place_type"))
    if raw is None:
        return ()
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.replace("|", ",").split(",")]
    elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray, str)):
        parts = [str(item).strip() for item in raw]
    else:
        parts = [str(raw).strip()]
    return tuple(part for part in parts if part)


def _coordinates(record: Mapping[str, Any]) -> GeoPoint | None:
    lat = _first(record, ("latitude", "lat"))
    lon = _first(record, ("longitude", "lon", "lng"))
    if lat is None or lon is None:
        location = record.get("location")
        if isinstance(location, Mapping):
            lat = _first(location, ("latitude", "lat"))
            lon = _first(location, ("longitude", "lon", "lng"))
    if lat is None or lon is None:
        return None
    try:
        return GeoPoint(float(lat), float(lon))
    except (TypeError, ValueError):
        raise ValueError("invalid latitude/longitude")


def stable_import_key(source_file: str, source_record_id: str) -> str:
    """Stable key for idempotent replay of one legacy source record."""
    payload = f"v1-json|{source_file}|{source_record_id}".encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True)
class V1ImportItem:
    record_index: int
    import_key: str
    source_file: str
    source_record_id: str
    disposition: str
    reason: str
    observation: IngestionObservation | None = None


@dataclass(frozen=True)
class V1ImportReport:
    source_file: str
    dry_run: bool
    items: tuple[V1ImportItem, ...]

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def ready(self) -> int:
        return sum(item.disposition == MigrationDisposition.READY for item in self.items)

    @property
    def skipped(self) -> int:
        return sum(item.disposition == MigrationDisposition.SKIPPED for item in self.items)

    @property
    def invalid(self) -> int:
        return sum(item.disposition == MigrationDisposition.INVALID for item in self.items)


@dataclass(frozen=True)
class V1MigrationPolicy:
    """Legacy field mapping policy; versioned independently from storage."""

    policy_version: str = "v1-json-import-1"
    source_name: str = "prachinlife-v1-json"


def convert_v1_record(
    record: Mapping[str, Any],
    *,
    source_file: str,
    record_index: int,
    policy: V1MigrationPolicy = V1MigrationPolicy(),
) -> V1ImportItem:
    """Convert one legacy mapping without mutating it or creating a Place."""
    explicit_id = _clean(_first(record, ("id", "place_id", "slug", "osm_id")))
    source_record_id = explicit_id or f"row-{record_index}"
    import_key = stable_import_key(source_file, source_record_id)

    name = _clean(_first(record, ("name", "title", "place_name")))
    if name is None:
        return V1ImportItem(
            record_index, import_key, source_file, source_record_id,
            MigrationDisposition.INVALID, "missing place name", None,
        )

    try:
        location = _coordinates(record)
    except ValueError as exc:
        return V1ImportItem(
            record_index, import_key, source_file, source_record_id,
            MigrationDisposition.INVALID, str(exc), None,
        )

    source = SourceRef(
        source_type=SourceType.OTHER,
        source_name=policy.source_name,
        source_record_id=f"{source_file}#{source_record_id}",
    )
    candidate = SourcePlaceCandidate(
        source=source,
        name=name,
        location=location,
        address_text=_clean(_first(record, ("address_text", "address", "formatted_address"))),
        province=_clean(_first(record, ("province", "province_name", "state"))),
        categories=_categories(record),
        phone=_clean(_first(record, ("phone", "telephone", "tel"))),
        website=_clean(_first(record, ("website", "url", "link"))),
        raw_attributes={
            "migration_policy_version": policy.policy_version,
            "legacy_source_file": source_file,
            "legacy_source_record_id": source_record_id,
            "legacy_record": dict(record),
            "import_key": import_key,
        },
    )
    normalized = normalize_candidate(candidate)
    observation = IngestionObservation(candidate=normalized, claims=build_claims(normalized))
    return V1ImportItem(
        record_index, import_key, source_file, source_record_id,
        MigrationDisposition.READY, "converted", observation,
    )


def build_v1_import_report(
    records: Iterable[Mapping[str, Any]],
    *,
    source_file: str,
    already_imported: Iterable[str] = (),
    dry_run: bool = True,
    policy: V1MigrationPolicy = V1MigrationPolicy(),
) -> V1ImportReport:
    """Create deterministic import plan and mark replayed records as skipped."""
    seen = set(already_imported)
    batch_seen: set[str] = set()
    items: list[V1ImportItem] = []
    for index, record in enumerate(records):
        converted = convert_v1_record(
            record, source_file=source_file, record_index=index, policy=policy
        )
        if converted.import_key in seen or converted.import_key in batch_seen:
            converted = V1ImportItem(
                converted.record_index,
                converted.import_key,
                converted.source_file,
                converted.source_record_id,
                MigrationDisposition.SKIPPED,
                "already imported",
                None,
            )
        batch_seen.add(converted.import_key)
        items.append(converted)
    return V1ImportReport(source_file=source_file, dry_run=dry_run, items=tuple(items))


def load_v1_json(path: str | Path) -> tuple[Mapping[str, Any], ...]:
    """Read a legacy JSON file without modifying it.

    Accepted shapes are a top-level list or a common wrapper containing a list
    under places/items/results/data. Anything else is rejected explicitly.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, Mapping):
        records = None
        for key in ("places", "items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
        if records is None:
            raise ValueError("unsupported V1 JSON shape")
    else:
        raise ValueError("unsupported V1 JSON shape")

    if not all(isinstance(item, Mapping) for item in records):
        raise ValueError("V1 JSON records must be objects")
    return tuple(records)
