from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from place_platform_v2.admin_drafts import (
    AdminDraftService,
    AdminDraftStatus,
    AdminDraftStore,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data/v2/place_platform_v2.sqlite3"
EXPORT = ROOT / "data/v2/exports/prachinlife_places_v2.json"
ADMIN = ROOT / "admin.html"
ADMIN_JS = ROOT / "js/admin/admin.js"
SERVER = ROOT / "scripts/admin_internal_server.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestPhase2U1AdminDraftPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.place = json.loads(EXPORT.read_text(encoding="utf-8"))["places"][0]

    def sample_update(self):
        return {
            "schema_version": "2T.4-v1",
            "intake": "admin_web",
            "mode": "evidence_draft_only",
            "operation": "update_place_candidate",
            "place_id": self.place["id"],
            "source": {
                "source_name": "OpenStreetMap",
                "source_url": "https://www.openstreetmap.org/",
            },
            "note": "2U.1 regression",
            "changes": [{"field_name": "description", "value": "ข้อมูลทดสอบ"}],
        }

    def test_u101_separate_draft_store_persists_pending_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "drafts.sqlite3"
            result = AdminDraftService(CANONICAL, db).persist(self.sample_update())
            self.assertEqual(result.status, AdminDraftStatus.PENDING_REVIEW)
            with AdminDraftStore(db) as store:
                self.assertEqual(store.count(), 1)
                self.assertEqual(store.list_pending()[0]["draft_id"], result.draft_id)

    def test_u102_canonical_database_is_byte_identical_after_persist(self):
        before = sha(CANONICAL)
        with tempfile.TemporaryDirectory() as tmp:
            AdminDraftService(CANONICAL, Path(tmp) / "drafts.sqlite3").persist(self.sample_update())
        self.assertEqual(sha(CANONICAL), before)

    def test_u103_update_rejects_unknown_canonical_place(self):
        payload = self.sample_update()
        payload["place_id"] = "00000000-0000-0000-0000-000000000000"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "does not exist"):
                AdminDraftService(CANONICAL, Path(tmp) / "drafts.sqlite3").persist(payload)

    def test_u104_create_gets_provisional_candidate_id_without_canonical_write(self):
        payload = self.sample_update()
        payload["operation"] = "create_place_candidate"
        payload["place_id"] = None
        payload["changes"] = [
            {"field_name": "canonical_name", "value": "ร้านทดสอบ"},
            {"field_name": "province", "value": "ปราจีนบุรี"},
            {"field_name": "location", "value": {"latitude": 14.05, "longitude": 101.37}},
            {"field_name": "categories", "value": ["restaurant"]},
        ]
        before = sha(CANONICAL)
        with tempfile.TemporaryDirectory() as tmp:
            result = AdminDraftService(CANONICAL, Path(tmp) / "drafts.sqlite3").persist(payload)
            self.assertIsNone(result.target_place_id)
            self.assertTrue(result.candidate_place_id)
        self.assertEqual(sha(CANONICAL), before)

    def test_u105_server_side_field_validation_is_reused(self):
        payload = self.sample_update()
        payload["changes"] = [{"field_name": "website", "value": "not-a-url"}]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, r"http\(s\) URL"):
                AdminDraftService(CANONICAL, Path(tmp) / "drafts.sqlite3").persist(payload)

    def test_u106_admin_has_explicit_save_pending_review_action(self):
        html = ADMIN.read_text(encoding="utf-8")
        js = ADMIN_JS.read_text(encoding="utf-8")
        self.assertIn('id="adminSaveDraftBtn"', html)
        self.assertIn('DRAFT_API_URL = "/api/admin/evidence-drafts"', js)
        self.assertIn('method: "POST"', js)
        self.assertIn("pending_review", js)

    def test_u107_internal_server_is_loopback_and_canonical_write_disabled(self):
        text = SERVER.read_text(encoding="utf-8")
        self.assertRegex(text, r"default=[\"']127\.0\.0\.1[\"']")
        self.assertIn('Canonical writes: DISABLED', text)
        self.assertRegex(text, r"[\"']canonical_write[\"']\s*:\s*False")
        self.assertNotIn("save_place(", text)
        self.assertNotIn("commit_adoption(", text)

    def test_u108_runtime_queue_is_gitignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/v2/admin_evidence_drafts.sqlite3", text)

    def test_u109_admin_cache_is_phase2u1(self):
        text = ADMIN.read_text(encoding="utf-8")
        self.assertRegex(text, r"phase2u(?:1|2|3|33|331)-20260822")

    def test_u110_public_index_does_not_load_admin_persistence(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("admin_internal_server", text)
        self.assertNotIn("/api/admin/evidence-drafts", text)


if __name__ == "__main__":
    unittest.main()
