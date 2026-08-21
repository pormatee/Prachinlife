"""Read-only audit of legacy V1 place JSON before V2 migration.

This module never writes to V1 files or to the V2 repository. It converts legacy
records through the Packet #11 migration contract and summarizes migration
readiness, missing fields, category/province coverage, and duplicate candidate
signals across files.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence
import json

from .migration import (
    MigrationDisposition,
    V1ImportItem,
    build_v1_import_report,
    load_v1_json,
)


@dataclass(frozen=True)
class FileAudit:
    path: str
    total: int
    ready: int
    skipped: int
    invalid: int
    missing_location: int
    missing_province: int
    missing_categories: int
    invalid_reasons: Mapping[str, int]
    provinces: Mapping[str, int]
    categories: Mapping[str, int]
    top_level_keys: Mapping[str, int]


@dataclass(frozen=True)
class DuplicateCandidateGroup:
    candidate_key: str
    occurrences: int
    records: tuple[str, ...]


@dataclass(frozen=True)
class MigrationAuditReport:
    files: tuple[FileAudit, ...]
    duplicate_candidate_groups: tuple[DuplicateCandidateGroup, ...]
    unreadable_files: Mapping[str, str]

    @property
    def total_records(self) -> int:
        return sum(item.total for item in self.files)

    @property
    def ready_records(self) -> int:
        return sum(item.ready for item in self.files)

    @property
    def skipped_records(self) -> int:
        return sum(item.skipped for item in self.files)

    @property
    def invalid_records(self) -> int:
        return sum(item.invalid for item in self.files)

    def to_dict(self) -> dict:
        return {
            "mode": "dry-run-read-only",
            "summary": {
                "files_audited": len(self.files),
                "total_records": self.total_records,
                "ready_records": self.ready_records,
                "skipped_records": self.skipped_records,
                "invalid_records": self.invalid_records,
                "duplicate_candidate_groups": len(self.duplicate_candidate_groups),
                "unreadable_files": len(self.unreadable_files),
            },
            "files": [asdict(item) for item in self.files],
            "duplicate_candidate_groups": [asdict(item) for item in self.duplicate_candidate_groups],
            "unreadable_files": dict(self.unreadable_files),
        }


def _audit_items(
    path: str,
    items: Sequence[V1ImportItem],
    records: Sequence[Mapping[str, object]],
) -> FileAudit:
    invalid_reasons: Counter[str] = Counter()
    provinces: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    missing_location = 0
    missing_province = 0
    missing_categories = 0
    top_level_keys: Counter[str] = Counter()

    for record in records:
        top_level_keys.update(str(key) for key in record.keys())

    for item in items:
        if item.disposition == MigrationDisposition.INVALID:
            invalid_reasons[item.reason] += 1
            continue
        if item.observation is None:
            continue
        candidate = item.observation.candidate
        if candidate.location is None:
            missing_location += 1
        if candidate.province:
            provinces[candidate.province] += 1
        else:
            missing_province += 1
        if candidate.categories:
            categories.update(candidate.categories)
        else:
            missing_categories += 1

    return FileAudit(
        path=path,
        total=len(items),
        ready=sum(i.disposition == MigrationDisposition.READY for i in items),
        skipped=sum(i.disposition == MigrationDisposition.SKIPPED for i in items),
        invalid=sum(i.disposition == MigrationDisposition.INVALID for i in items),
        missing_location=missing_location,
        missing_province=missing_province,
        missing_categories=missing_categories,
        invalid_reasons=dict(sorted(invalid_reasons.items())),
        provinces=dict(sorted(provinces.items())),
        categories=dict(sorted(categories.items())),
        top_level_keys=dict(sorted(top_level_keys.items())),
    )


def audit_v1_files(paths: Iterable[str | Path]) -> MigrationAuditReport:
    """Audit files read-only and aggregate potential duplicate candidate keys."""
    file_results: list[FileAudit] = []
    unreadable: dict[str, str] = {}
    key_records: defaultdict[str, list[str]] = defaultdict(list)

    for raw_path in paths:
        path = Path(raw_path)
        label = str(path)
        try:
            records = load_v1_json(path)
            report = build_v1_import_report(records, source_file=path.name, dry_run=True)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            unreadable[label] = str(exc)
            continue

        file_results.append(_audit_items(label, report.items, records))
        for item in report.items:
            if item.disposition != MigrationDisposition.READY or item.observation is None:
                continue
            key = item.observation.candidate.candidate_key
            if not key:
                continue
            key_records[key].append(f"{path.name}#{item.source_record_id}")

    duplicates = tuple(
        DuplicateCandidateGroup(key, len(records), tuple(sorted(records)))
        for key, records in sorted(key_records.items())
        if len(records) > 1
    )
    return MigrationAuditReport(tuple(file_results), duplicates, dict(sorted(unreadable.items())))


def discover_v1_place_json(root: str | Path = ".") -> tuple[Path, ...]:
    """Find likely V1 place datasets conservatively.

    Auto-discovery is deliberately limited to index-like JSON files directly
    under the repository root. Historical backups, archives, candidates, test
    fixtures, generated/normalized copies, and workflow files must be supplied
    explicitly if an operator wants to audit them. This keeps the default audit
    aligned with the currently published V1 datasets instead of inflating counts
    with historical copies.
    """
    root_path = Path(root)
    candidates = [
        path
        for path in root_path.glob("*.json")
        if path.is_file() and "index" in path.name.lower()
    ]
    return tuple(sorted(candidates, key=lambda p: str(p)))
