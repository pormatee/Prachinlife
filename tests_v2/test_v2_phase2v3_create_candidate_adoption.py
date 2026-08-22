from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
import sqlite3
import tempfile
import unittest

from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.controlled_candidate_adoption import (
    CREATE_POLICY_VERSION,
    _canonical_from_assessment,
    _latest_approved_create,
    assess_approved_create_candidate,
    commit_approved_create_candidate,
)
from place_platform_v2.controlled_adoption import _draft_evidence
from place_platform_v2.adoption import PlaceRevision
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.sqlite_store import SQLitePlaceRepository


class TestPhase2V3CreateCandidateAdoption(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.canonical = root / "canonical.sqlite3"
        self.drafts = root / "drafts.sqlite3"
        with SQLitePlaceRepository(self.canonical):
            pass

    def tearDown(self): self.tmp.cleanup()

    def _create(self, *, name="ร้านใหม่", lat=14.10, lon=101.20, province="ปราจีนบุรี", categories=("fuel",), phone=None, description=None, source_url="https://example.com/new"):
        changes = [
            {"field_name":"canonical_name","value":name},
            {"field_name":"location","value":{"latitude":lat,"longitude":lon}},
            {"field_name":"province","value":province},
            {"field_name":"categories","value":list(categories)},
        ]
        if phone: changes.append({"field_name":"phone","value":phone})
        if description: changes.append({"field_name":"description","value":description})
        saved = AdminDraftService(self.canonical,self.drafts).persist({
            "mode":"evidence_draft_only","operation":"create_place_candidate","place_id":None,
            "source":{"source_name":"admin-source","source_url":source_url},"changes":changes,
        })
        with AdminDraftStore(self.drafts) as store:
            store.review(saved.draft_id,AdminDraftStatus.APPROVED)
        return saved

    def _seed(self, *, name="ร้านเดิม", lat=14.0, lon=101.0, phone=None):
        place=CanonicalPlace(identity=PlaceIdentity(),canonical_name=name,location=GeoPoint(lat,lon),province="ปราจีนบุรี",categories=("fuel",),phone=phone)
        with SQLitePlaceRepository(self.canonical) as repo: repo.save_place(place)
        return place

    def test_v301_dry_run_new_candidate_is_read_only_and_adoptable(self):
        d=self._create()
        before=self.canonical.read_bytes()
        a=assess_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(a.result,"adoptable"); self.assertEqual(a.resolution_outcome,"new")
        self.assertTrue(a.canonical_unchanged); self.assertEqual(self.canonical.read_bytes(),before)

    def test_v302_exact_duplicate_is_blocked(self):
        self._seed(name="Caltex",lat=14.12,lon=101.23)
        d=self._create(name="Caltex",lat=14.12,lon=101.23)
        a=assess_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(a.result,"reconcilable_existing")
        self.assertEqual(a.resolution_outcome,"matched")
        self.assertIsNotNone(a.target_place_id)

    def test_v303_ambiguous_nearby_candidate_is_blocked_for_review(self):
        self._seed(name="Caltex Station",lat=14.1200,lon=101.2300)
        d=self._create(name="Caltex Statio",lat=14.1202,lon=101.2302)
        a=assess_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(a.resolution_outcome,"review"); self.assertEqual(a.result,"blocked_duplicate_or_review")

    def test_v304_required_identity_fields_need_supported_evidence(self):
        saved=AdminDraftService(self.canonical,self.drafts).persist({
            "mode":"evidence_draft_only","operation":"create_place_candidate","place_id":None,
            "source":{"source_name":"admin-source","source_url":"https://example.com/missing"},
            "changes":[{"field_name":"canonical_name","value":"Incomplete"}],
        })
        with AdminDraftStore(self.drafts) as store: store.review(saved.draft_id,AdminDraftStatus.APPROVED)
        a=assess_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=saved.draft_id)
        self.assertEqual(a.result,"blocked_verification")
        self.assertEqual(set(a.missing_required_fields),{"location","province","categories"})

    def test_v305_unapproved_create_cannot_commit(self):
        saved=AdminDraftService(self.canonical,self.drafts).persist({
            "mode":"evidence_draft_only","operation":"create_place_candidate","place_id":None,
            "source":{"source_name":"admin-source","source_url":"https://example.com/pending"},
            "changes":[{"field_name":"canonical_name","value":"Pending"}],
        })
        with self.assertRaisesRegex(ValueError,"latest approved create"):
            commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=saved.draft_id)

    def test_v306_commit_creates_canonical_with_candidate_id(self):
        d=self._create(name="Caltex New",phone="0812345678")
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(r.result,"committed"); self.assertEqual(r.place_id,d.candidate_place_id)
        with SQLitePlaceRepository(self.canonical) as repo:
            place=repo.get_place(d.candidate_place_id)
            self.assertEqual(place.canonical_name,"Caltex New"); self.assertEqual(place.phone,"0812345678")

    def test_v307_all_evidence_preserved_including_noncanonical_detail(self):
        d=self._create(description="ปั๊ม")
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo:
            evidence=repo.list_evidence(r.place_id)
        self.assertEqual(len(evidence),5)
        self.assertIn("description",{e.field_name for e in evidence})

    def test_v308_creation_revision_receipt_and_resolution_audit_exist(self):
        d=self._create()
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo:
            revisions=repo.list_revisions(r.place_id)
            receipt=repo.get_admin_adoption_receipt(d.draft_id)
            audit=repo.get_admin_candidate_resolution_audit(d.draft_id)
        self.assertEqual(len(revisions),1); self.assertIsNotNone(receipt); self.assertIsNotNone(audit)
        self.assertEqual(audit["resolution_outcome"],"new")
        self.assertFalse(audit["decision"]["publication_performed"])

    def test_v309_commit_is_idempotent(self):
        d=self._create()
        first=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        second=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(first.result,"committed"); self.assertEqual(second.result,"already_committed")
        with SQLitePlaceRepository(self.canonical) as repo:
            self.assertEqual(len(repo.list_revisions(first.place_id)),1)

    def test_v310_publication_is_never_performed(self):
        d=self._create()
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertFalse(r.publication_performed)
        con=sqlite3.connect(self.canonical)
        try:
            self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='published_places'").fetchone())
        finally: con.close()

    def test_v311_blocked_duplicate_does_not_mutate_canonical(self):
        seeded=self._seed(name="Caltex",lat=14.12,lon=101.23)
        d=self._create(name="Caltex",lat=14.12,lon=101.23)
        with SQLitePlaceRepository(self.canonical) as repo:
            before_place = repo.get_place(seeded.identity.place_id)
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(r.result,"reconciled_existing")
        with SQLitePlaceRepository(self.canonical) as repo:
            self.assertEqual(repo.get_place(seeded.identity.place_id), before_place)

    def test_v312_atomic_store_rolls_back_on_duplicate_evidence_id(self):
        first_draft=self._create(name="Atomic Seed",lat=14.20,lon=101.30)
        first=commit_approved_create_candidate(
            canonical_database=self.canonical,draft_database=self.drafts,draft_id=first_draft.draft_id
        )
        with SQLitePlaceRepository(self.canonical) as repo:
            collision_id=repo.list_evidence(first.place_id)[0].evidence_id
            places_before=repo.canonical_place_count()
            evidence_before=repo.evidence_count()

        second=self._create(name="Atomic Failure",lat=14.40,lon=101.50,source_url="https://example.com/atomic-failure")
        assessment=assess_approved_create_candidate(
            canonical_database=self.canonical,draft_database=self.drafts,draft_id=second.draft_id
        )
        self.assertEqual(assessment.result,"adoptable")
        when=datetime.now(timezone.utc)
        place=_canonical_from_assessment(
            place_id=second.candidate_place_id,fields=assessment.fields,created_at=when
        )
        with AdminDraftStore(self.drafts) as drafts:
            item=_latest_approved_create(drafts,second.draft_id)
            evidence=list(_draft_evidence(item))
        # Deliberately collide after the place INSERT has begun. The whole transaction
        # must roll back: no place, evidence, revision, receipt, or audit may remain.
        evidence[0]=type(evidence[0])(
            evidence_id=collision_id,place_id=evidence[0].place_id,source=evidence[0].source,
            kind=evidence[0].kind,field_name=evidence[0].field_name,value=evidence[0].value,
            status=evidence[0].status,observed_at=evidence[0].observed_at,metadata=evidence[0].metadata,
        )
        fields=tuple(f.field_name for f in assessment.fields if f.acceptable and f.selected_value is not None)
        revision=PlaceRevision(
            revision_id=str(uuid4()),place_id=second.candidate_place_id,changed_fields=fields,
            before_values={f:(() if f=="categories" else None) for f in fields},
            after_values={f:getattr(place,f) for f in fields},reason="forced atomic rollback test",
            evidence_ids=tuple(e.evidence_id for e in evidence),policy_version=CREATE_POLICY_VERSION,created_at=when,
        )
        with SQLitePlaceRepository(self.canonical) as repo:
            with self.assertRaisesRegex(ValueError,"failed atomically"):
                repo.commit_admin_candidate_creation(
                    draft_id=second.draft_id,place=place,revision=revision,evidence=evidence,
                    policy_version=CREATE_POLICY_VERSION,
                    decision={"operation":"create_place_candidate","resolution_outcome":"new","publication_performed":False},
                    committed_at=when,
                )
            self.assertIsNone(repo.get_place(second.candidate_place_id))
            self.assertIsNone(repo.get_admin_adoption_receipt(second.draft_id))
            self.assertIsNone(repo.get_admin_candidate_resolution_audit(second.draft_id))
            self.assertEqual(repo.canonical_place_count(),places_before)
            self.assertEqual(repo.evidence_count(),evidence_before)

    def test_v313_review_database_is_not_mutated_by_commit(self):
        d=self._create()
        before=self.drafts.read_bytes()
        commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(self.drafts.read_bytes(),before)


if __name__ == "__main__": unittest.main()
