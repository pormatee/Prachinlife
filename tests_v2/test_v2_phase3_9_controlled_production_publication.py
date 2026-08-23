import json
import shutil
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.controlled_production_publication import (
    FILES,
    STAGING_REL,
    commit_controlled_production_publication,
    plan_controlled_production_publication,
    rollback_controlled_production_publication,
)
from place_platform_v2.publication_impact_preview import _production_mapping, _revision_scope
from place_platform_v2.comparative_release_gate import audit_fresh_comparative_release
from place_platform_v2.production_readiness_gate import audit_production_readiness

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/v2/place_platform_v2.sqlite3"


class Phase39ControlledProductionPublicationTests(unittest.TestCase):
    def fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "repo"
        root.mkdir()
        db = root / "data/v2/place_platform_v2.sqlite3"
        db.parent.mkdir(parents=True)
        shutil.copy2(DB, db)
        for fn in FILES:
            shutil.copy2(ROOT / fn, root / fn)
        shutil.copytree(ROOT / STAGING_REL, root / STAGING_REL)
        shutil.copy2(ROOT / "app.js", root / "app.js")
        reports = root / "data/v2/discovery_reports"
        reports.mkdir(parents=True, exist_ok=True)
        old = ROOT / "data/v2/discovery_reports/phase2h_comparative_beta_ready.json"
        if old.exists():
            shutil.copy2(old, reports / old.name)

        # Normalize the fixture to the pre-publication state so the test suite is
        # deterministic whether the repository snapshot itself is pre- or post-publish.
        revisions = _revision_scope(db)
        pids = {x["place_id"] for x in revisions}
        mapping = _production_mapping(db, pids)
        by_place = {}
        for rev in revisions:
            by_place.setdefault(rev["place_id"], {})[rev["field_name"]] = rev.get("before_value")
        for fn in FILES:
            for base in [root, root / STAGING_REL]:
                path = base / fn
                rows = json.loads(path.read_text(encoding="utf-8"))
                idx = {str(row.get("id", "")): row for row in rows if isinstance(row, dict)}
                changed = False
                for pid, refs in mapping.items():
                    for mapped_fn, rid in refs:
                        if mapped_fn != fn or rid not in idx:
                            continue
                        row = idx[rid]
                        md = dict(row.get("metadata") or {})
                        for field, before in by_place.get(pid, {}).items():
                            md[field] = before
                        row["metadata"] = md
                        row.pop("external_links", None)
                        changed = True
                if changed:
                    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return td, root, db

    def test_plan_ready_and_readonly(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        before_db = db.read_bytes()
        before_prod = {fn: (root / fn).read_bytes() for fn in FILES}
        before_stage = {fn: (root / STAGING_REL / fn).read_bytes() for fn in FILES}
        x = plan_controlled_production_publication(repo_root=root, database_path=db)
        self.assertEqual(x["status"], "READY_TO_PUBLISH")
        self.assertEqual(x["changed_record_count"], 6)
        self.assertEqual(x["targeted_record_count"], 6)
        self.assertEqual(x["targeted_field_impact_counts"], {"phone": 6, "website": 2})
        self.assertEqual(db.read_bytes(), before_db)
        self.assertEqual(before_prod, {fn: (root / fn).read_bytes() for fn in FILES})
        self.assertEqual(before_stage, {fn: (root / STAGING_REL / fn).read_bytes() for fn in FILES})

    def test_commit_and_idempotency(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        x = commit_controlled_production_publication(repo_root=root, database_path=db)
        self.assertEqual(x["status"], "PUBLISHED")
        self.assertEqual(x["published_record_count"], 6)
        self.assertTrue(x["rollback_available"])
        self.assertEqual(x["post_comparative_status"], "PASS")
        self.assertEqual(x["post_readiness_status"], "READY")
        y = commit_controlled_production_publication(repo_root=root, database_path=db)
        self.assertEqual(y["status"], "ALREADY_PUBLISHED")
        self.assertTrue(y["already_published"])
        self.assertEqual(y["published_record_count"], 0)

    def test_publication_preserves_shape_and_syncs_staging(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        before = json.loads((root / "vegetarian_index.json").read_text(encoding="utf-8"))
        before_by_id = {str(r.get("id")): r for r in before}
        commit_controlled_production_publication(repo_root=root, database_path=db)
        prod = json.loads((root / "vegetarian_index.json").read_text(encoding="utf-8"))
        stage = json.loads((root / STAGING_REL / "vegetarian_index.json").read_text(encoding="utf-8"))
        prod_by_id = {str(r.get("id")): r for r in prod}
        stage_by_id = {str(r.get("id")): r for r in stage}
        changed = [rid for rid in prod_by_id if prod_by_id[rid] != before_by_id[rid]]
        self.assertEqual(len(changed), 6)
        for rid in changed:
            self.assertNotIn("v2_preview_overlay", prod_by_id[rid].get("metadata", {}))
            self.assertEqual(prod_by_id[rid], stage_by_id[rid])

    def test_post_publication_release_gates_pass(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        commit_controlled_production_publication(repo_root=root, database_path=db)
        c = audit_fresh_comparative_release(root, db, root / STAGING_REL)
        p = audit_production_readiness(root, db, root / STAGING_REL)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["fallback_mutations"], [])
        self.assertEqual(p["status"], "READY")

    def test_backup_covers_production_and_staging(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        x = commit_controlled_production_publication(repo_root=root, database_path=db)
        b = Path(x["backup_dir"])
        self.assertTrue((b / "backup_manifest.json").exists())
        for fn in FILES:
            self.assertTrue((b / "production" / fn).exists())
            self.assertTrue((b / "staging" / fn).exists())

    def test_explicit_rollback_restores_both_snapshots(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        prod_before = {fn: (root / fn).read_bytes() for fn in FILES}
        stage_before = {fn: (root / STAGING_REL / fn).read_bytes() for fn in FILES}
        x = commit_controlled_production_publication(repo_root=root, database_path=db)
        y = rollback_controlled_production_publication(repo_root=root, release_id=x["release_id"])
        self.assertEqual(y["status"], "ROLLED_BACK")
        self.assertTrue(y["rollback_hashes_verified"])
        self.assertEqual(prod_before, {fn: (root / fn).read_bytes() for fn in FILES})
        self.assertEqual(stage_before, {fn: (root / STAGING_REL / fn).read_bytes() for fn in FILES})

    def test_database_unchanged(self):
        td, root, db = self.fixture(); self.addCleanup(td.cleanup)
        before = db.read_bytes()
        x = commit_controlled_production_publication(repo_root=root, database_path=db)
        self.assertEqual(db.read_bytes(), before)
        self.assertTrue(x["safety"]["database_unchanged"])


if __name__ == "__main__":
    unittest.main()
