from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ID = "801410d8-00e5-58e9-b77e-f681bbdf6f5c"


def community_payload(place_id=CANONICAL_ID):
    return {
        "schema_version": "prachinlife-contribution-v1",
        "mode": "evidence_draft_only",
        "operation": "update_place_candidate",
        "place_id": place_id,
        "source": {
            "source_name": "Community supplied source",
            "source_url": "https://example.com/community-report",
        },
        "note": "community report",
        "changes": [{"field_name": "description", "value": "reported value"}],
        "contribution_metadata": {
            "origin": "public_suggest_edit",
            "handoff": "manual_admin_import",
            "canonical_write": False,
            "publication": False,
            "trust_tier": "untrusted_community_report",
            "adoption_eligible": False,
            "admin_approval_eligible": False,
            "requires_independent_verification": True,
        },
    }


class Phase15FinalSafetyTest(unittest.TestCase):
    def _dbs(self):
        td = tempfile.TemporaryDirectory()
        base = Path(td.name)
        canonical = base / "canonical.sqlite3"
        drafts = base / "drafts.sqlite3"
        con = sqlite3.connect(canonical)
        con.execute("CREATE TABLE places(place_id TEXT PRIMARY KEY, canonical_name TEXT, description TEXT)")
        con.execute("INSERT INTO places VALUES(?,?,?)", (CANONICAL_ID, "อาหารเจ ซั่นสี่", "ORIGINAL"))
        con.commit(); con.close()
        return td, canonical, drafts

    def test_1521_public_renderers_expose_canonical_v2_bridge(self):
        for rel in ("app.js", "js/modules/vegetarian.js", "js/modules/go.js", "js/modules/service.js"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("data-v2-place-id=", text, rel)
            self.assertIn("metadata?.v2_place_id", text, rel)

    def test_1522_contribution_prefers_canonical_v2_id(self):
        text = (ROOT / "js/core/place-contribution.js").read_text(encoding="utf-8")
        self.assertIn("card.dataset.v2PlaceId || card.dataset.placeId", text)

    def test_1523_sansi_published_bridge_points_to_real_canonical(self):
        rows = json.loads((ROOT / "vegetarian_index.json").read_text(encoding="utf-8"))
        row = next(x for x in rows if x.get("id") == "web-prachinburi-sansi-jay")
        self.assertEqual(row["metadata"]["v2_place_id"], CANONICAL_ID)
        con = sqlite3.connect(ROOT / "data/v2/place_platform_v2.sqlite3")
        try:
            self.assertIsNotNone(con.execute("SELECT 1 FROM places WHERE place_id=?", (CANONICAL_ID,)).fetchone())
        finally:
            con.close()

    def test_1524_public_envelope_is_explicitly_untrusted_and_ineligible(self):
        text = (ROOT / "js/core/place-contribution.js").read_text(encoding="utf-8")
        for marker in (
            'trust_tier: "untrusted_community_report"',
            'adoption_eligible: false',
            'admin_approval_eligible: false',
            'requires_independent_verification: true',
        ):
            self.assertIn(marker, text)

    def test_1525_importer_requires_hardened_safety_metadata(self):
        text = (ROOT / "js/admin/contribution-import.js").read_text(encoding="utf-8")
        self.assertIn('meta.trust_tier !== "untrusted_community_report"', text)
        self.assertIn("meta.adoption_eligible !== false", text)
        self.assertIn("meta.requires_independent_verification !== true", text)

    def test_1526_community_report_persists_candidate_only(self):
        td, canonical, drafts = self._dbs()
        with td:
            result = AdminDraftService(canonical, drafts).persist(community_payload())
            self.assertEqual(result.status, AdminDraftStatus.PENDING_REVIEW)
            con = sqlite3.connect(canonical)
            try:
                self.assertEqual(con.execute("SELECT description FROM places WHERE place_id=?", (CANONICAL_ID,)).fetchone()[0], "ORIGINAL")
            finally:
                con.close()
            with AdminDraftStore(drafts) as store:
                evidence = store.list_for_review()[0]["evidence"]
            self.assertEqual({e["status"] for e in evidence}, {"candidate"})

    def test_1527_admin_approve_cannot_bypass_community_hold(self):
        td, canonical, drafts = self._dbs()
        with td:
            result = AdminDraftService(canonical, drafts).persist(community_payload())
            with AdminDraftStore(drafts) as store:
                with self.assertRaisesRegex(ValueError, "HOLD-only"):
                    store.review(result.draft_id, AdminDraftStatus.APPROVED, "looks okay")
                current = store.list_for_review()[0]
                self.assertEqual(current["status"], AdminDraftStatus.PENDING_REVIEW)
            con = sqlite3.connect(canonical)
            try:
                self.assertEqual(con.execute("SELECT description FROM places WHERE place_id=?", (CANONICAL_ID,)).fetchone()[0], "ORIGINAL")
            finally:
                con.close()

    def test_1528_community_report_can_be_rejected(self):
        td, canonical, drafts = self._dbs()
        with td:
            result = AdminDraftService(canonical, drafts).persist(community_payload())
            with AdminDraftStore(drafts) as store:
                review = store.review(result.draft_id, AdminDraftStatus.REJECTED, "unverified community report")
                self.assertEqual(review["review_status"], AdminDraftStatus.REJECTED)

    def test_1529_operator_draft_approval_behavior_remains_available(self):
        td, canonical, drafts = self._dbs()
        with td:
            payload = community_payload()
            payload.pop("contribution_metadata")
            payload["source"] = {"source_name":"PrachinLife Admin Operator", "source_url":"https://example.com/verified-source"}
            result = AdminDraftService(canonical, drafts).persist(payload)
            with AdminDraftStore(drafts) as store:
                review = store.review(result.draft_id, AdminDraftStatus.APPROVED, "verified independently")
                self.assertEqual(review["review_status"], AdminDraftStatus.APPROVED)

    def test_1530_review_ui_hides_direct_approve_for_community_reports(self):
        text = (ROOT / "js/admin/review.js").read_text(encoding="utf-8")
        self.assertIn("COMMUNITY REPORT • HOLD", text)
        self.assertIn("communityReport(item)", text)
        self.assertIn("Operator Evidence Draft", text)


if __name__ == "__main__":
    unittest.main()
