from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.phase16_verified_update import run_phase16
from place_platform_v2.sqlite_store import SQLitePlaceRepository

ROOT = Path(__file__).resolve().parents[1]
REAL_DB = ROOT / "data/v2/place_platform_v2.sqlite3"
PID = "16161616-1616-4616-8616-161616161616"
NOW = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)


def verified_input(path: Path, *, value: str = "0899999999") -> Path:
    payload = [
        {
            "place_id": PID,
            "field_name": "phone",
            "value": value,
            "source_name": "Independent Official Source",
            "source_url": "https://example.com/phase16/verified/place",
            "observed_at": "2026-08-24T10:00:00+00:00",
            "trust_tier": "operator_verified_independent_source",
            "community_report": False,
            "community_source_url": "https://example.net/community/report",
            "operator_note": "Phase 16 isolated fixture verification",
        }
    ]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def make_clean_db(path: Path) -> None:
    repo = SQLitePlaceRepository(path)
    try:
        repo.save_place(
            CanonicalPlace(
                identity=PlaceIdentity(PID),
                canonical_name="Phase 16 Fixture Place",
                location=GeoPoint(14.0, 101.0),
                province="ปราจีนบุรี",
                categories=("restaurant",),
                phone=None,
                website=None,
                lifecycle=PlaceLifecycle.ACTIVE,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    finally:
        repo.close()


def current_phone(db: Path):
    import sqlite3
    con = sqlite3.connect(db)
    try:
        return con.execute(
            "SELECT phone FROM places WHERE place_id=?",
            (PID,),
        ).fetchone()[0]
    finally:
        con.close()


class Phase16FinalOrchestrationGateV2Test(unittest.TestCase):
    def fixture(self):
        td = tempfile.TemporaryDirectory()
        base = Path(td.name)
        repo = base / "repo"
        repo.mkdir()

        db = repo / "data/v2/place_platform_v2.sqlite3"
        db.parent.mkdir(parents=True)
        make_clean_db(db)

        updates = verified_input(base / "verified.json")
        return td, repo, db, updates

    def test_1613_clean_fixture_has_no_historical_adoption_state(self):
        td, repo, db, updates = self.fixture()
        self.addCleanup(td.cleanup)

        import sqlite3
        con = sqlite3.connect(db)
        try:
            self.assertEqual(
                con.execute("SELECT COUNT(*) FROM place_evidence").fetchone()[0],
                0,
            )
            self.assertEqual(
                con.execute("SELECT COUNT(*) FROM place_revisions").fetchone()[0],
                0,
            )
        finally:
            con.close()

    def test_1614_commit_path_runs_adoption_publication_and_post_verify(self):
        td, repo, db, updates = self.fixture()
        self.addCleanup(td.cleanup)

        before_phone = current_phone(db)

        with patch(
            "place_platform_v2.phase16_verified_update.plan_controlled_production_publication",
            return_value={"status": "READY_TO_PUBLISH", "blockers": []},
        ), patch(
            "place_platform_v2.phase16_verified_update.commit_controlled_production_publication",
            return_value={
                "status": "PUBLISHED",
                "release_id": "fixture-release-1",
                "rollback_available": True,
            },
        ) as commit_pub, patch(
            "place_platform_v2.phase16_verified_update.verify_post_publication",
            return_value={"status": "PASS"},
        ):
            result = run_phase16(
                repo_root=repo,
                database_path=db,
                verified_updates_path=updates,
                commit=True,
            )

        self.assertEqual(result["status"], "PUBLISHED")
        self.assertTrue(result["canonical_rollback_available"])
        self.assertTrue(result["publication_rollback_available"])
        commit_pub.assert_called_once()

        self.assertNotEqual(before_phone, current_phone(db))
        self.assertEqual(current_phone(db), "0899999999")

        import sqlite3
        con = sqlite3.connect(db)
        try:
            self.assertEqual(
                con.execute(
                    "SELECT COUNT(*) FROM place_revisions WHERE place_id=?",
                    (PID,),
                ).fetchone()[0],
                1,
            )
        finally:
            con.close()

    def test_1615_post_failure_restores_byte_identical_canonical_db_and_calls_publication_rollback(self):
        td, repo, db, updates = self.fixture()
        self.addCleanup(td.cleanup)

        before = db.read_bytes()

        with patch(
            "place_platform_v2.phase16_verified_update.plan_controlled_production_publication",
            return_value={"status": "READY_TO_PUBLISH", "blockers": []},
        ), patch(
            "place_platform_v2.phase16_verified_update.commit_controlled_production_publication",
            return_value={
                "status": "PUBLISHED",
                "release_id": "fixture-release-rollback",
                "rollback_available": True,
            },
        ), patch(
            "place_platform_v2.phase16_verified_update.verify_post_publication",
            return_value={"status": "FAIL"},
        ), patch(
            "place_platform_v2.phase16_verified_update.rollback_controlled_production_publication",
            return_value={
                "status": "ROLLED_BACK",
                "release_id": "fixture-release-rollback",
                "rollback_hashes_verified": True,
            },
        ) as rollback_pub:
            with self.assertRaisesRegex(
                RuntimeError,
                "post publication verification failed",
            ):
                run_phase16(
                    repo_root=repo,
                    database_path=db,
                    verified_updates_path=updates,
                    commit=True,
                )

        rollback_pub.assert_called_once()
        self.assertEqual(db.read_bytes(), before)

    def test_1616_plan_block_restores_byte_identical_db_without_publication(self):
        td, repo, db, updates = self.fixture()
        self.addCleanup(td.cleanup)

        before = db.read_bytes()

        with patch(
            "place_platform_v2.phase16_verified_update.plan_controlled_production_publication",
            return_value={
                "status": "BLOCKED",
                "blockers": ["fixture-blocker"],
            },
        ), patch(
            "place_platform_v2.phase16_verified_update.commit_controlled_production_publication",
        ) as commit_pub:
            with self.assertRaisesRegex(RuntimeError, "publication blocked"):
                run_phase16(
                    repo_root=repo,
                    database_path=db,
                    verified_updates_path=updates,
                    commit=True,
                )

        commit_pub.assert_not_called()
        self.assertEqual(db.read_bytes(), before)

    def test_1617_real_production_db_is_never_mutated(self):
        before = REAL_DB.read_bytes()

        td, repo, db, updates = self.fixture()
        self.addCleanup(td.cleanup)

        self.assertNotEqual(db.resolve(), REAL_DB.resolve())

        with patch(
            "place_platform_v2.phase16_verified_update.plan_controlled_production_publication",
            return_value={"status": "BLOCKED", "blockers": ["fixture-only"]},
        ):
            with self.assertRaises(RuntimeError):
                run_phase16(
                    repo_root=repo,
                    database_path=db,
                    verified_updates_path=updates,
                    commit=True,
                )

        self.assertEqual(REAL_DB.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
