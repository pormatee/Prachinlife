from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.controlled_production_switch import (
    FILES,
    commit_production_switch,
    plan_production_switch,
    rollback_production_switch,
)

ROOT = Path(__file__).resolve().parents[1]


class TestControlledProductionSwitch(unittest.TestCase):
    def make_fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "repo"
        root.mkdir()
        for rel in ["place_platform_v2", "data/v2/staging", "data/v2/discovery_reports"]:
            (root / rel).mkdir(parents=True, exist_ok=True)
        # Copy only the files needed by comparative/readiness gates.
        for filename in FILES:
            shutil.copy2(ROOT / filename, root / filename)
        shutil.copy2(ROOT / "app.js", root / "app.js")
        shutil.copytree(ROOT / "data/v2/staging/user_web", root / "data/v2/staging/user_web")
        shutil.copy2(ROOT / "data/v2/place_platform_v2.sqlite3", root / "data/v2/place_platform_v2.sqlite3")
        old = ROOT / "data/v2/discovery_reports/phase2h_comparative_beta_ready.json"
        if old.exists():
            shutil.copy2(old, root / "data/v2/discovery_reports/phase2h_comparative_beta_ready.json")
        return td, root

    def test_switch_01_dry_run_does_not_mutate_production(self):
        td, root = self.make_fixture()
        try:
            before = {f: (root / f).read_bytes() for f in FILES}
            r = plan_production_switch(root, root / "data/v2/place_platform_v2.sqlite3", root / "data/v2/staging/user_web")
            self.assertEqual(r["status"], "READY_TO_SWITCH")
            self.assertEqual(before, {f: (root / f).read_bytes() for f in FILES})
        finally:
            td.cleanup()

    def test_switch_02_commit_promotes_exact_staging_files(self):
        td, root = self.make_fixture()
        try:
            r = commit_production_switch(root, root / "data/v2/place_platform_v2.sqlite3", root / "data/v2/staging/user_web")
            self.assertEqual(r["status"], "SWITCHED")
            for f in FILES:
                self.assertEqual((root / f).read_bytes(), (root / "data/v2/staging/user_web" / f).read_bytes())
            self.assertTrue(r["rollback_available"])
        finally:
            td.cleanup()

    def test_switch_03_commit_does_not_change_database(self):
        td, root = self.make_fixture()
        try:
            db = root / "data/v2/place_platform_v2.sqlite3"
            before = db.read_bytes()
            commit_production_switch(root, db, root / "data/v2/staging/user_web")
            self.assertEqual(before, db.read_bytes())
        finally:
            td.cleanup()

    def test_switch_04_manual_rollback_restores_exact_v1_files(self):
        td, root = self.make_fixture()
        try:
            before = {f: (root / f).read_bytes() for f in FILES}
            r = commit_production_switch(root, root / "data/v2/place_platform_v2.sqlite3", root / "data/v2/staging/user_web")
            rr = rollback_production_switch(root, r["release_id"])
            self.assertEqual(rr["status"], "ROLLED_BACK")
            self.assertTrue(rr["rollback_hashes_verified"])
            self.assertEqual(before, {f: (root / f).read_bytes() for f in FILES})
        finally:
            td.cleanup()

    def test_switch_05_backup_manifest_covers_all_production_files(self):
        td, root = self.make_fixture()
        try:
            r = commit_production_switch(root, root / "data/v2/place_platform_v2.sqlite3", root / "data/v2/staging/user_web")
            manifest = json.loads((Path(r["backup_dir"]) / "backup_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(set(manifest["files"]), set(FILES))
        finally:
            td.cleanup()

    def test_switch_06_audit_records_switch_without_deleting_backup(self):
        td, root = self.make_fixture()
        try:
            r = commit_production_switch(root, root / "data/v2/place_platform_v2.sqlite3", root / "data/v2/staging/user_web")
            audit = json.loads((root / "data/v2/discovery_reports/v2_production_switch_current.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["status"], "SWITCHED")
            self.assertTrue(Path(audit["backup_dir"]).exists())
            self.assertFalse(audit["database_changed"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
