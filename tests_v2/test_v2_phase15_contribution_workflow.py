from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_JS = ROOT / "js/core/place-contribution.js"
IMPORT_JS = ROOT / "js/admin/contribution-import.js"

def base_payload():
    return {
        "schema_version": "prachinlife-contribution-v1",
        "mode": "evidence_draft_only",
        "operation": "update_place_candidate",
        "place_id": "11111111-1111-4111-8111-111111111111",
        "source": {
            "source_name": "Official source",
            "source_url": "https://example.com/place-1",
        },
        "note": "Public Suggest Edit contribution",
        "changes": [
            {"field_name": "phone", "value": "037-123456"},
            {"field_name": "opening_hours", "value": "08:00-17:00"},
        ],
        "contribution_metadata": {
            "origin": "public_suggest_edit",
            "handoff": "manual_admin_import",
            "canonical_write": False,
            "publication": False,
        },
    }

class Phase15ContributionWorkflowTest(unittest.TestCase):
    def test_1501_public_contract_is_manual_handoff(self):
        text = PUBLIC_JS.read_text(encoding="utf-8")
        self.assertIn('"manual_admin_import"', text)
        self.assertIn("canonical_write: false", text)
        self.assertIn("publication: false", text)
        self.assertNotIn('fetch("/api/admin/evidence-drafts"', text)

    def test_1502_public_fields_are_detail_only(self):
        text = PUBLIC_JS.read_text(encoding="utf-8")
        for field in ("phone","website","opening_hours","description","real_image","address_text"):
            self.assertIn(f'"{field}"', text)
        self.assertNotIn('"canonical_name",', text)
        self.assertNotIn('"lifecycle",', text)

    def test_1503_admin_import_posts_to_existing_draft_endpoint(self):
        text = IMPORT_JS.read_text(encoding="utf-8")
        self.assertIn('fetch("/api/admin/evidence-drafts"', text)
        self.assertIn('"evidence_draft_only"', text)
        self.assertNotIn("/approve", text)
        self.assertIn('meta.canonical_write !== false', text)
        self.assertIn('meta.publication !== false', text)
        self.assertIn('meta.trust_tier !== "untrusted_community_report"', text)

    def test_1504_end_to_end_import_creates_pending_candidate_only(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            canonical = td / "canonical.sqlite3"
            drafts = td / "drafts.sqlite3"
            con = sqlite3.connect(canonical)
            con.execute("CREATE TABLE places(place_id TEXT PRIMARY KEY, canonical_name TEXT, phone TEXT)")
            con.execute("INSERT INTO places VALUES(?,?,?)", ("11111111-1111-4111-8111-111111111111","Test Place","OLD"))
            con.commit(); con.close()

            result = AdminDraftService(canonical, drafts).persist(base_payload())
            self.assertEqual(result.status, AdminDraftStatus.PENDING_REVIEW)
            self.assertEqual(result.target_place_id, "11111111-1111-4111-8111-111111111111")
            self.assertEqual(result.changes_count, 2)

            con = sqlite3.connect(canonical)
            row = con.execute("SELECT phone FROM places WHERE place_id='11111111-1111-4111-8111-111111111111'").fetchone()
            con.close()
            self.assertEqual(row[0], "OLD")

            with AdminDraftStore(drafts) as store:
                item = store.list_for_review()[0]
            statuses = {e["status"] for e in item["evidence"]}
            self.assertEqual(statuses, {"candidate"})

    def test_1505_duplicate_submission_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            canonical = td / "canonical.sqlite3"
            drafts = td / "drafts.sqlite3"
            con = sqlite3.connect(canonical)
            con.execute("CREATE TABLE places(place_id TEXT PRIMARY KEY)")
            con.execute("INSERT INTO places VALUES(?)", ("11111111-1111-4111-8111-111111111111",))
            con.commit(); con.close()

            service = AdminDraftService(canonical, drafts)
            first = service.persist(base_payload())
            second = service.persist(base_payload())
            self.assertEqual(first.draft_id, second.draft_id)
            with AdminDraftStore(drafts) as store:
                self.assertEqual(store.count(), 1)

    def test_1506_unknown_place_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            canonical = td / "canonical.sqlite3"
            drafts = td / "drafts.sqlite3"
            con = sqlite3.connect(canonical)
            con.execute("CREATE TABLE places(place_id TEXT PRIMARY KEY)")
            con.commit(); con.close()
            with self.assertRaises(ValueError):
                AdminDraftService(canonical, drafts).persist(base_payload())

    def test_1507_identity_and_lifecycle_fields_not_accepted_by_public_importer(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node unavailable")
        source = IMPORT_JS.read_text(encoding="utf-8")
        script = f"""
const vm=require("vm");
const context={{window:{{}},document:{{readyState:"loading",addEventListener:()=>{{}},getElementById:()=>({{}})}}}};
vm.createContext(context); vm.runInContext({json.dumps(source)},context);
const v=context.window.PrachinLifeContributionImport.validate;
const p={json.dumps(base_payload())};
p.changes=[{{field_name:"lifecycle",value:"active"}}];
try{{v(p);console.log("BAD")}}catch(e){{console.log("PASS")}}
"""
        out = subprocess.check_output([node,"-e",script], cwd=ROOT, text=True).strip()
        self.assertEqual(out, "PASS")

    def test_1508_static_public_ui_is_loaded_after_place_detail(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("js/core/place-contribution.js", index)
        self.assertLess(
            index.index("js/core/place-detail.js"),
            index.index("js/core/place-contribution.js"),
        )

    def test_1509_import_page_exists_and_has_review_link(self):
        html = (ROOT / "admin-contribution-import.html").read_text(encoding="utf-8")
        self.assertIn("admin-review.html", html)
        self.assertIn("contribution-import.js", html)

    def test_1510_public_ui_has_no_personal_identity_collection(self):
        text = PUBLIC_JS.read_text(encoding="utf-8")
        self.assertNotIn('name="email"', text)
        self.assertNotIn('name="user_name"', text)
        self.assertNotIn('name="phone_contact"', text)

if __name__ == "__main__":
    unittest.main()
