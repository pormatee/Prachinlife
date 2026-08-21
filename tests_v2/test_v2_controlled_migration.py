from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from place_platform_v2.controlled_migration import (
    build_controlled_migration_batch,
    execute_controlled_migration,
)
from place_platform_v2.sqlite_store import SQLitePlaceRepository


def record(record_id, name="ร้านหนึ่ง", *, lat=14.1, lon=101.2, category="restaurant", province="ปราจีนบุรี"):
    return {
        "id": record_id,
        "title": name,
        "category": category,
        "location": {
            "province": province,
            "latitude": lat,
            "longitude": lon,
        },
        "metadata": {"phone": "0812345678"},
    }


class TestControlledMigration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "places.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, rows):
        path = self.root / name
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return path

    def test_01_dry_run_never_writes_database(self):
        path = self.write("go_index.json", [record("a")])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=True)
            self.assertEqual(batch.report.ready_records, 1)
            self.assertEqual(repo.canonical_place_count(), 0)
            self.assertEqual(repo.migration_import_count(), 0)

    def test_02_dry_run_cannot_be_committed(self):
        path = self.write("go_index.json", [record("a")])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=True)
            with self.assertRaises(ValueError):
                execute_controlled_migration(batch, repo)

    def test_03_commit_persists_place_evidence_and_ledger(self):
        path = self.write("go_index.json", [record("a")])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            execute_controlled_migration(batch, repo)
            self.assertEqual(repo.canonical_place_count(), 1)
            self.assertGreater(repo.evidence_count(), 0)
            self.assertEqual(repo.migration_import_count(), 1)

    def test_04_database_reopen_preserves_migration(self):
        path = self.write("go_index.json", [record("a")])
        with SQLitePlaceRepository(self.db) as repo:
            execute_controlled_migration(
                build_controlled_migration_batch([path], repository=repo, dry_run=False), repo
            )
        with SQLitePlaceRepository(self.db) as repo:
            self.assertEqual(repo.canonical_place_count(), 1)
            self.assertEqual(repo.migration_import_count(), 1)
            self.assertGreater(repo.evidence_count(), 0)

    def test_05_replay_is_idempotent(self):
        path = self.write("go_index.json", [record("a")])
        with SQLitePlaceRepository(self.db) as repo:
            first = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            execute_controlled_migration(first, repo)
            counts = (repo.canonical_place_count(), repo.evidence_count(), repo.migration_import_count())
            replay = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            self.assertEqual(replay.report.ready_records, 0)
            self.assertEqual(replay.report.already_imported_records, 1)
            execute_controlled_migration(replay, repo)
            self.assertEqual(counts, (repo.canonical_place_count(), repo.evidence_count(), repo.migration_import_count()))

    def test_06_geo_anchored_duplicate_across_files_becomes_one_place(self):
        left = self.write("go_index.json", [record("go-a", name="วัดตัวอย่าง")])
        right = self.write("prachinlife_index.json", [record("feed-b", name="วัดตัวอย่าง")])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([left, right], repository=repo, dry_run=False)
            self.assertEqual(batch.report.ready_records, 2)
            self.assertEqual(batch.report.canonical_places, 1)
            execute_controlled_migration(batch, repo)
            self.assertEqual(repo.canonical_place_count(), 1)
            self.assertEqual(repo.migration_import_count(), 2)

    def test_07_same_name_without_coordinates_is_not_auto_merged(self):
        a = record("a", name="ชื่อซ้ำ", lat=None, lon=None)
        b = record("b", name="ชื่อซ้ำ", lat=None, lon=None)
        left = self.write("a.json", [a])
        right = self.write("b.json", [b])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([left, right], repository=repo, dry_run=False)
            self.assertEqual(batch.report.canonical_places, 2)

    def test_08_categories_are_unioned_for_exact_duplicate(self):
        left = self.write("go_index.json", [record("a", category="attraction")])
        right = self.write("prachinlife_index.json", [record("b", category="recommended")])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([left, right], repository=repo, dry_run=False)
            self.assertEqual(batch.report.canonical_places, 1)
            self.assertEqual(set(batch.places[0].categories), {"attraction", "recommended"})

    def test_09_non_place_records_are_skipped(self):
        row = record("promo")
        row["category"] = "shopping"
        path = self.write("prachinlife_index.json", [row])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            self.assertEqual(batch.report.skipped_records, 1)
            self.assertEqual(batch.report.ready_records, 0)
            self.assertEqual(batch.report.canonical_places, 0)

    def test_10_invalid_record_blocks_commit(self):
        path = self.write("bad.json", [{"id": "x", "location": {"latitude": 14, "longitude": 101}}])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            self.assertEqual(batch.report.invalid_records, 1)
            with self.assertRaises(ValueError):
                execute_controlled_migration(batch, repo)
            self.assertEqual(repo.canonical_place_count(), 0)

    def test_11_commit_is_atomic_on_ledger_conflict(self):
        path = self.write("go_index.json", [record("a"), record("b", name="ร้านสอง", lat=14.2)])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            # Corrupt the batch deliberately by duplicating one ledger row. The
            # transaction must leave no place/evidence behind.
            broken = type(batch)(batch.places, batch.evidence, batch.ledger + (batch.ledger[0],), batch.report)
            with self.assertRaises(ValueError):
                execute_controlled_migration(broken, repo)
            self.assertEqual(repo.canonical_place_count(), 0)
            self.assertEqual(repo.evidence_count(), 0)
            self.assertEqual(repo.migration_import_count(), 0)

    def test_12_migration_does_not_write_published_store(self):
        path = self.write("go_index.json", [record("a")])
        with SQLitePlaceRepository(self.db) as repo:
            execute_controlled_migration(
                build_controlled_migration_batch([path], repository=repo, dry_run=False), repo
            )
            tables = {row[0] for row in repo._connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("published_places", tables)

    def test_13_ledger_tracks_each_source_record_of_duplicate(self):
        left = self.write("go_index.json", [record("a")])
        right = self.write("feed.json", [record("b")])
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([left, right], repository=repo, dry_run=False)
            execute_controlled_migration(batch, repo)
            rows = repo._connection.execute("SELECT source_file, source_record_id FROM migration_imports ORDER BY source_file").fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["source_file"] for row in rows}, {"feed.json", "go_index.json"})

    def test_14_place_ids_are_deterministic_across_fresh_databases(self):
        path = self.write("go_index.json", [record("a")])
        ids = []
        for dbname in ("one.sqlite", "two.sqlite"):
            with SQLitePlaceRepository(self.root / dbname) as repo:
                batch = build_controlled_migration_batch([path], repository=repo, dry_run=True)
                ids.append(batch.places[0].identity.place_id)
        self.assertEqual(ids[0], ids[1])

    def test_15_source_json_is_not_modified(self):
        path = self.write("go_index.json", [record("a")])
        before = path.read_bytes()
        with SQLitePlaceRepository(self.db) as repo:
            batch = build_controlled_migration_batch([path], repository=repo, dry_run=False)
            execute_controlled_migration(batch, repo)
        self.assertEqual(path.read_bytes(), before)

    def test_16_migration_schema_is_versioned_without_mutating_packet10_store_contract(self):
        from place_platform_v2.sqlite_store import MIGRATION_SCHEMA_VERSION, SQLITE_SCHEMA_VERSION
        self.assertEqual(SQLITE_SCHEMA_VERSION, "2.0-packet10")
        self.assertEqual(MIGRATION_SCHEMA_VERSION, "1.0-packet13")

    def test_17_runner_defaults_to_dry_run(self):
        from scripts.migrate_v1_to_v2_sqlite import parser
        args = parser().parse_args([])
        self.assertFalse(args.commit)

    def test_18_runner_bootstraps_repo_root_when_executed_directly(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "migrate_v1_to_v2_sqlite.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
