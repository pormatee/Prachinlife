from __future__ import annotations
import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.controlled_candidate_adoption import assess_approved_create_candidate, commit_approved_create_candidate
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.sqlite_store import SQLitePlaceRepository

class TestPhase2V32ExistingCanonicalReconciliation(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); root=Path(self.t.name)
        self.canonical=root/'canonical.sqlite3'; self.drafts=root/'drafts.sqlite3'
        with SQLitePlaceRepository(self.canonical): pass
    def tearDown(self): self.t.cleanup()

    def seed(self,name,lat,lon):
        place=CanonicalPlace(identity=PlaceIdentity(),canonical_name=name,location=GeoPoint(lat,lon),province='ปราจีนบุรี',categories=('fuel',))
        with SQLitePlaceRepository(self.canonical) as repo: repo.save_place(place)
        return place

    def draft(self,name='คาลเท็กซ์',lat=13.7709337,lon=102.0231286):
        saved=AdminDraftService(self.canonical,self.drafts).persist({
            'mode':'evidence_draft_only','operation':'create_place_candidate','place_id':None,
            'source':{'source_name':'Admin','source_url':'https://www.caltex.com/'},
            'changes':[
                {'field_name':'canonical_name','value':name},
                {'field_name':'location','value':{'latitude':lat,'longitude':lon}},
                {'field_name':'province','value':'ปราจีนบุรี'},
                {'field_name':'categories','value':['fuel']},
                {'field_name':'description','value':'ปั๊ม'},
                {'field_name':'real_image','value':'http://127.0.0.1/media/caltex.jpg'},
            ],
        })
        with AdminDraftStore(self.drafts) as store: store.review(saved.draft_id,AdminDraftStatus.APPROVED)
        return saved

    def test_v321_exact_match_dominates_nearby_review_for_reconciliation(self):
        exact=self.seed('คาลเท็กซ์',13.7709337,102.0231286)
        self.seed('NGV',13.7708243,102.0222039)
        d=self.draft()
        a=assess_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(a.result,'reconcilable_existing')
        self.assertEqual(a.target_place_id,exact.identity.place_id)
        self.assertEqual(a.exact_match_count,1); self.assertGreaterEqual(a.review_candidate_count,1)

    def test_v322_reconciliation_never_overwrites_canonical_fields(self):
        exact=self.seed('คาลเท็กซ์',13.7709337,102.0231286); d=self.draft()
        with SQLitePlaceRepository(self.canonical) as repo: before=repo.get_place(exact.identity.place_id)
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(r.result,'reconciled_existing'); self.assertEqual(r.changed_fields,())
        with SQLitePlaceRepository(self.canonical) as repo:
            after=repo.get_place(exact.identity.place_id); receipt=repo.get_admin_adoption_receipt(d.draft_id); audit=repo.get_admin_candidate_resolution_audit(d.draft_id)
        self.assertEqual(before,after); self.assertEqual(tuple(receipt['revision_ids']),())
        self.assertFalse(audit['decision']['canonical_field_overwrite']); self.assertFalse(audit['decision']['publication_performed'])

    def test_v323_all_candidate_evidence_is_preserved_and_rebound_with_origin(self):
        exact=self.seed('คาลเท็กซ์',13.7709337,102.0231286); d=self.draft()
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo: evidence=repo.list_evidence(exact.identity.place_id)
        fields={e.field_name for e in evidence}
        self.assertIn('description',fields); self.assertIn('real_image',fields)
        admin=[e for e in evidence if e.metadata.get('admin_candidate_draft_id')==d.draft_id]
        self.assertEqual(len(admin),6)
        self.assertTrue(all(e.metadata['admin_candidate_original_place_id']==d.candidate_place_id for e in admin))
        self.assertTrue(all(e.place_id==exact.identity.place_id for e in admin))
        self.assertEqual(r.place_id,exact.identity.place_id)

    def test_v324_reconciliation_is_idempotent(self):
        exact=self.seed('คาลเท็กซ์',13.7709337,102.0231286); d=self.draft()
        first=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo: count1=repo.evidence_count()
        second=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        with SQLitePlaceRepository(self.canonical) as repo: count2=repo.evidence_count()
        self.assertEqual(first.result,'reconciled_existing'); self.assertEqual(second.result,'already_committed'); self.assertEqual(count1,count2)

    def test_v325_multiple_deterministic_matches_stay_blocked(self):
        self.seed('คาลเท็กซ์',13.7709337,102.0231286); self.seed('คาลเท็กซ์',13.7709337,102.0231286); d=self.draft()
        a=assess_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(a.result,'blocked_duplicate_or_review'); self.assertEqual(a.exact_match_count,2)
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=d.draft_id)
        self.assertEqual(r.result,'blocked')

if __name__=='__main__': unittest.main()
