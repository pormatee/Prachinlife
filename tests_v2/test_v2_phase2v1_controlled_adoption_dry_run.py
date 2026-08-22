from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.controlled_adoption import build_controlled_adoption_dry_run
from place_platform_v2.contracts import GeoPoint, SourceRef, SourceType
from place_platform_v2.models import CanonicalPlace, PlaceEvidence, PlaceIdentity, EvidenceKind
from place_platform_v2.sqlite_store import SQLitePlaceRepository


class TestPhase2V1ControlledAdoptionDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.canonical = root / "canonical.sqlite3"
        self.drafts = root / "drafts.sqlite3"
        self.place = CanonicalPlace(
            identity=PlaceIdentity(), canonical_name="ร้านเดิม", location=GeoPoint(14.0, 101.0),
            province="ปราจีนบุรี", categories=("restaurant",), phone="0100000000",
        )
        with SQLitePlaceRepository(self.canonical) as repo:
            repo.save_place(self.place)
            now = datetime.now(timezone.utc)
            repo.add_evidence(PlaceEvidence(
                place_id=self.place.identity.place_id,
                source=SourceRef(SourceType.WEB, "official", source_url="https://example.com/a", observed_at=now),
                kind=EvidenceKind.CONTACT, field_name="phone", value="0200000000", observed_at=now,
            ))

    def tearDown(self): self.tmp.cleanup()

    def _approve(self, changes, operation="update_place_candidate", place_id=None):
        service = AdminDraftService(self.canonical, self.drafts)
        payload = {
            "mode":"evidence_draft_only", "operation":operation,
            "place_id": self.place.identity.place_id if place_id is None and operation.startswith("update") else place_id,
            "source":{"source_name":"official", "source_url":"https://example.com/a"},
            "changes": changes,
        }
        saved = service.persist(payload)
        with AdminDraftStore(self.drafts) as store:
            store.review(saved.draft_id, AdminDraftStatus.APPROVED)
        return saved

    def test_v101_dry_run_is_read_only(self):
        self._approve([{"field_name":"phone","value":"0200000000"}])
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        self.assertTrue(report.canonical_unchanged)
        self.assertEqual(report.mode, "DRY_RUN")

    def test_v102_supported_contact_can_be_proposed(self):
        self._approve([{"field_name":"phone","value":"0200000000"}])
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        phone = report.drafts[0].fields[0]
        self.assertEqual(phone.verification_outcome, "supported")
        self.assertEqual(phone.adoption_outcome, "proposed")

    def test_v103_high_risk_single_source_is_blocked(self):
        self._approve([{"field_name":"canonical_name","value":"ชื่อใหม่"}])
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        field = report.drafts[0].fields[0]
        self.assertEqual(field.adoption_outcome, "blocked")

    def test_v104_noncanonical_detail_fields_are_explicitly_blocked(self):
        self._approve([{"field_name":"description","value":"รายละเอียดใหม่"}])
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        self.assertEqual(report.drafts[0].blocked_fields, ("description",))

    def test_v105_create_candidate_is_not_adopted_in_2v1(self):
        self._approve([{"field_name":"canonical_name","value":"ร้านใหม่"}], operation="create_place_candidate", place_id=None)
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        self.assertEqual(report.drafts[0].result, "blocked")
        self.assertIn("new-place", report.drafts[0].reason)

    def test_v106_only_latest_approved_groups_are_evaluated(self):
        first = self._approve([{"field_name":"phone","value":"0200000000"}])
        service = AdminDraftService(self.canonical, self.drafts)
        saved = service.persist({
            "mode":"evidence_draft_only", "operation":"update_place_candidate", "place_id":self.place.identity.place_id,
            "source":{"source_name":"official","source_url":"https://example.com/a"},
            "changes":[{"field_name":"phone","value":"0300000000"}],
        })
        with AdminDraftStore(self.drafts) as store: store.review(saved.draft_id, AdminDraftStatus.APPROVED)
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        self.assertEqual(report.approved_groups, 1)
        self.assertEqual(report.drafts[0].draft_id, saved.draft_id)

    def test_v107_dry_run_does_not_add_evidence_or_revision(self):
        self._approve([{"field_name":"phone","value":"0200000000"}])
        with SQLitePlaceRepository(self.canonical) as repo:
            before = (repo.evidence_count(), len(repo.list_revisions(self.place.identity.place_id)) if hasattr(repo,'list_revisions') else 0)
        build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        with SQLitePlaceRepository(self.canonical) as repo:
            self.assertEqual(repo.evidence_count(), before[0])
            self.assertEqual(repo.get_place(self.place.identity.place_id).phone, "0100000000")

    def test_v108_report_counts_proposals(self):
        self._approve([{"field_name":"phone","value":"0200000000"}])
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        self.assertEqual(report.proposed_field_changes, 1)
        self.assertEqual(report.adoptable_drafts, 1)

    def test_v109_dry_run_does_not_mutate_review_database(self):
        self._approve([{"field_name":"phone","value":"0200000000"}])
        before = self.drafts.read_bytes()
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=self.drafts)
        self.assertTrue(report.draft_unchanged)
        self.assertEqual(self.drafts.read_bytes(), before)

    def test_v110_missing_draft_database_is_not_created(self):
        missing = Path(self.tmp.name) / "missing-drafts.sqlite3"
        report = build_controlled_adoption_dry_run(canonical_database=self.canonical, draft_database=missing)
        self.assertFalse(missing.exists())
        self.assertTrue(report.draft_unchanged)
        self.assertEqual(report.approved_groups, 0)


if __name__ == "__main__": unittest.main()
