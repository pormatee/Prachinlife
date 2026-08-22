from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.contracts import GeoPoint, SourceRef, SourceType
from place_platform_v2.controlled_adoption_commit import commit_approved_draft
from place_platform_v2.models import CanonicalPlace, PlaceEvidence, PlaceIdentity, EvidenceKind
from place_platform_v2.sqlite_store import SQLitePlaceRepository


class TestPhase2V2ControlledCanonicalCommit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.canonical = root / "canonical.sqlite3"
        self.drafts = root / "drafts.sqlite3"
        self.place = CanonicalPlace(
            identity=PlaceIdentity(), canonical_name="ร้านเดิม", location=GeoPoint(14.0,101.0),
            province="ปราจีนบุรี", categories=("restaurant",), phone="0100000000",
        )
        now = datetime.now(timezone.utc)
        with SQLitePlaceRepository(self.canonical) as repo:
            repo.save_place(self.place)
            repo.add_evidence(PlaceEvidence(
                place_id=self.place.identity.place_id,
                source=SourceRef(SourceType.WEB,"official",source_url="https://example.com/a",observed_at=now),
                kind=EvidenceKind.CONTACT,field_name="phone",value="0200000000",observed_at=now,
            ))

    def tearDown(self): self.tmp.cleanup()

    def _approved(self, changes, operation="update_place_candidate", place_id="AUTO"):
        if place_id == "AUTO": place_id = self.place.identity.place_id if operation == "update_place_candidate" else None
        saved = AdminDraftService(self.canonical,self.drafts).persist({
            "mode":"evidence_draft_only","operation":operation,"place_id":place_id,
            "source":{"source_name":"official","source_url":"https://example.com/a"},"changes":changes,
        })
        with AdminDraftStore(self.drafts) as store: store.review(saved.draft_id,AdminDraftStatus.APPROVED)
        return saved

    def test_v201_supported_contact_commits(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        result=commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(result.result,"committed")
        with SQLitePlaceRepository(self.canonical) as repo: self.assertEqual(repo.get_place(self.place.identity.place_id).phone,"0200000000")

    def test_v202_revision_and_receipt_are_written(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo:
            self.assertEqual(len(repo.list_revisions(self.place.identity.place_id)),1)
            self.assertIsNotNone(repo.get_admin_adoption_receipt(d.draft_id))

    def test_v203_approved_evidence_is_persisted(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        with SQLitePlaceRepository(self.canonical) as repo: before=repo.evidence_count()
        commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo: self.assertEqual(repo.evidence_count(),before+1)

    def test_v204_commit_is_idempotent(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        first=commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        second=commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(first.result,"committed"); self.assertEqual(second.result,"already_committed")
        with SQLitePlaceRepository(self.canonical) as repo: self.assertEqual(len(repo.list_revisions(self.place.identity.place_id)),1)

    def test_v205_create_candidate_is_blocked(self):
        d=self._approved([{"field_name":"canonical_name","value":"ร้านใหม่"}],operation="create_place_candidate")
        with self.assertRaisesRegex(ValueError,"existing canonical updates only"):
            commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)

    def test_v206_unapproved_draft_is_blocked(self):
        saved=AdminDraftService(self.canonical,self.drafts).persist({
            "mode":"evidence_draft_only","operation":"update_place_candidate","place_id":self.place.identity.place_id,
            "source":{"source_name":"official","source_url":"https://example.com/a"},
            "changes":[{"field_name":"phone","value":"0200000000"}],
        })
        with self.assertRaisesRegex(ValueError,"latest approved"):
            commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=saved.draft_id)

    def test_v207_high_risk_single_source_does_not_mutate(self):
        d=self._approved([{"field_name":"canonical_name","value":"ชื่อใหม่"}])
        result=commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(result.result,"blocked")
        with SQLitePlaceRepository(self.canonical) as repo: self.assertEqual(repo.get_place(self.place.identity.place_id).canonical_name,"ร้านเดิม")

    def test_v208_publication_not_performed(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        result=commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertFalse(result.publication_performed)

    def test_v209_draft_review_state_is_not_mutated(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        before=self.drafts.read_bytes()
        commit_approved_draft(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(self.drafts.read_bytes(),before)

    def test_v210_atomic_batch_rejects_duplicate_and_rolls_back(self):
        d=self._approved([{"field_name":"phone","value":"0200000000"}])
        with SQLitePlaceRepository(self.canonical) as repo:
            original=repo.get_place(self.place.identity.place_id)
            evidence=repo.list_evidence(self.place.identity.place_id)[0]
            from place_platform_v2.adoption import PlaceRevision
            from uuid import uuid4
            rev=PlaceRevision(str(uuid4()),self.place.identity.place_id,("phone",),{"phone":original.phone},{"phone":"x"},"test",(evidence.evidence_id,),"test",datetime.now(timezone.utc))
            changed=CanonicalPlace(identity=original.identity,canonical_name=original.canonical_name,location=original.location,address_text=original.address_text,province=original.province,categories=original.categories,phone="x",website=original.website,lifecycle=original.lifecycle,created_at=original.created_at,updated_at=datetime.now(timezone.utc))
            with self.assertRaises(ValueError):
                repo.commit_admin_adoption_batch(draft_id=d.draft_id,place=changed,revisions=(rev,),evidence=(evidence,),policy_version="test",committed_at=datetime.now(timezone.utc))
        with SQLitePlaceRepository(self.canonical) as repo: self.assertEqual(repo.get_place(self.place.identity.place_id).phone,"0100000000")

if __name__ == "__main__": unittest.main()
