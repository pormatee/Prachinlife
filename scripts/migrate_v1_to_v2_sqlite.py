#!/usr/bin/env python3
"""Controlled migration runner for the four V1 production indexes.

Dry-run is the default. Pass --commit explicitly to write the isolated V2
SQLite database. The script never edits legacy JSON and never publishes data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from place_platform_v2.controlled_migration import (
    build_controlled_migration_batch,
    execute_controlled_migration,
)
from place_platform_v2.sqlite_store import SQLitePlaceRepository


DEFAULT_FILES = (
    "go_index.json",
    "prachinlife_index.json",
    "service_index.json",
    "vegetarian_index.json",
)
DEFAULT_DATABASE = "data/v2/place_platform_v2.sqlite3"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("paths", nargs="*", help="V1 JSON paths; defaults to production root indexes")
    result.add_argument("--db", default=DEFAULT_DATABASE, help="isolated V2 SQLite path")
    result.add_argument("--commit", action="store_true", help="persist migration; otherwise dry-run only")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    paths = tuple(Path(value) for value in (args.paths or DEFAULT_FILES))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        print("ERROR missing source files:")
        for path in missing:
            print(f"  {path}")
        return 2

    db_path = Path(args.db)
    dry_run = not args.commit
    if args.commit:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    print("===== PRACHINLIFE V1 -> V2 CONTROLLED MIGRATION =====")
    print(f"mode={'COMMIT' if args.commit else 'DRY-RUN'}")
    print(f"database={db_path}")

    with SQLitePlaceRepository(db_path if args.commit else ":memory:") as repository:
        batch = build_controlled_migration_batch(paths, repository=repository, dry_run=dry_run)
        report = batch.report
        print(f"source_files={len(report.source_files)}")
        print(f"input_records={report.input_records}")
        print(f"ready_records={report.ready_records}")
        print(f"skipped_records={report.skipped_records}")
        print(f"invalid_records={report.invalid_records}")
        print(f"already_imported_records={report.already_imported_records}")
        print(f"canonical_places_planned={report.canonical_places}")
        print(f"evidence_records_planned={report.evidence_records}")

        if report.invalid_records:
            print("RESULT=BLOCKED_INVALID_RECORDS")
            return 3

        if not args.commit:
            print("database_writes=0")
            print("RESULT=DRY_RUN_PASS")
            return 0

        execute_controlled_migration(batch, repository)
        print(f"database_canonical_places={repository.canonical_place_count()}")
        print(f"database_evidence_records={repository.evidence_count()}")
        print(f"database_import_ledger={repository.migration_import_count()}")
        print("published_write=NO")
        print("RESULT=COMMIT_PASS")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
