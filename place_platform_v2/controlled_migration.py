"""Controlled V1 -> V2 migration execution.

This module turns READY V1 import items into deterministic canonical places and
field-level evidence, then commits them through one atomic SQLite migration
boundary. It never writes published_places and never mutates V1 JSON files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from uuid import NAMESPACE_URL, uuid5

from .contracts import EvidenceStatus
from .migration import (
    MigrationDisposition,
    V1ImportItem,
    build_v1_import_report,
    load_v1_json,
)
from .models import CanonicalPlace, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from .sqlite_store import SQLitePlaceRepository


MIGRATION_POLICY_VERSION = "v1-to-v2-controlled-1"


@dataclass(frozen=True)
class MigrationLedgerEntry:
    import_key: str
    source_file: str
    source_record_id: str
    candidate_key: str
    place_id: str


@dataclass(frozen=True)
class ControlledMigrationReport:
    dry_run: bool
    source_files: tuple[str, ...]
    input_records: int
    ready_records: int
    skipped_records: int
    invalid_records: int
    already_imported_records: int
    canonical_places: int
    evidence_records: int

    @property
    def can_commit(self) -> bool:
        return self.invalid_records == 0


@dataclass(frozen=True)
class MigrationBatch:
    places: tuple[CanonicalPlace, ...]
    evidence: tuple[PlaceEvidence, ...]
    ledger: tuple[MigrationLedgerEntry, ...]
    report: ControlledMigrationReport


def _place_id_for_item(item: V1ImportItem) -> str:
    assert item.observation is not None
    candidate = item.observation.candidate
    # A candidate fingerprint is safe as migration identity only when it has a
    # geographic anchor. Without coordinates, preserve source-record identity
    # rather than merging same-name branches silently.
    identity_key = candidate.candidate_key if candidate.location is not None else item.import_key
    return str(uuid5(NAMESPACE_URL, f"prachinlife-v2-place|{identity_key}"))


def _evidence_id(import_key: str, field_name: str, ordinal: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"prachinlife-v2-evidence|{import_key}|{field_name}|{ordinal}"))


def _build_place(group: Sequence[V1ImportItem], place_id: str) -> CanonicalPlace:
    ordered = sorted(group, key=lambda item: item.import_key)
    candidates = [item.observation.candidate for item in ordered if item.observation is not None]
    if not candidates:
        raise ValueError("migration place group has no observations")

    first = candidates[0]
    categories = tuple(sorted({category for c in candidates for category in c.categories}))

    def first_value(field: str):
        for candidate in candidates:
            value = getattr(candidate, field)
            if value not in (None, ""):
                return value
        return None

    return CanonicalPlace(
        identity=PlaceIdentity(place_id=place_id),
        canonical_name=first.name,
        location=first_value("location"),
        address_text=first_value("address_text"),
        province=first_value("province"),
        categories=categories,
        phone=first_value("phone"),
        website=first_value("website"),
        # Migration populates internal canonical storage only. Publication is a
        # separate explicit step, so legacy rows are not auto-activated here.
        lifecycle=PlaceLifecycle.UNKNOWN,
    )


def build_controlled_migration_batch(
    source_paths: Iterable[str | Path],
    *,
    repository: SQLitePlaceRepository,
    dry_run: bool = True,
) -> MigrationBatch:
    paths = tuple(Path(path) for path in source_paths)
    imported = repository.list_migration_import_keys()

    all_items: list[V1ImportItem] = []
    total = ready = skipped = invalid = already = 0
    source_files: list[str] = []

    for path in paths:
        source_file = path.name
        source_files.append(source_file)
        records = load_v1_json(path)
        report = build_v1_import_report(
            records,
            source_file=source_file,
            already_imported=imported,
            dry_run=dry_run,
        )
        total += report.total
        ready += report.ready
        skipped += report.skipped
        invalid += report.invalid
        already += sum(item.reason == "already imported" for item in report.items)
        all_items.extend(report.items)

    ready_items = [
        item for item in all_items
        if item.disposition == MigrationDisposition.READY and item.observation is not None
    ]

    grouped: dict[str, list[V1ImportItem]] = {}
    item_place_ids: dict[str, str] = {}
    for item in ready_items:
        place_id = _place_id_for_item(item)
        item_place_ids[item.import_key] = place_id
        grouped.setdefault(place_id, []).append(item)

    places = tuple(
        _build_place(grouped[place_id], place_id)
        for place_id in sorted(grouped)
    )

    evidence: list[PlaceEvidence] = []
    ledger: list[MigrationLedgerEntry] = []
    for item in sorted(ready_items, key=lambda value: value.import_key):
        observation = item.observation
        assert observation is not None
        place_id = item_place_ids[item.import_key]
        for ordinal, claim in enumerate(observation.claims):
            evidence.append(
                PlaceEvidence(
                    place_id=place_id,
                    source=claim.source,
                    kind=claim.kind,
                    field_name=claim.field_name,
                    value=claim.value,
                    status=EvidenceStatus.CANDIDATE,
                    evidence_id=_evidence_id(item.import_key, claim.field_name, ordinal),
                    metadata={
                        "import_key": item.import_key,
                        "migration_policy_version": MIGRATION_POLICY_VERSION,
                    },
                )
            )
        ledger.append(
            MigrationLedgerEntry(
                import_key=item.import_key,
                source_file=item.source_file,
                source_record_id=item.source_record_id,
                candidate_key=observation.candidate.candidate_key,
                place_id=place_id,
            )
        )

    result = ControlledMigrationReport(
        dry_run=dry_run,
        source_files=tuple(source_files),
        input_records=total,
        ready_records=ready,
        skipped_records=skipped,
        invalid_records=invalid,
        already_imported_records=already,
        canonical_places=len(places),
        evidence_records=len(evidence),
    )
    return MigrationBatch(places, tuple(evidence), tuple(ledger), result)


def execute_controlled_migration(batch: MigrationBatch, repository: SQLitePlaceRepository) -> ControlledMigrationReport:
    if batch.report.dry_run:
        raise ValueError("dry-run batch cannot be committed")
    if not batch.report.can_commit:
        raise ValueError("migration batch contains invalid records")
    repository.commit_migration_batch(batch.places, batch.evidence, batch.ledger)
    return batch.report
