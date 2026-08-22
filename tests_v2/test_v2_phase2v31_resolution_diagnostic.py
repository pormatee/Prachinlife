from __future__ import annotations
import tempfile, unittest
from pathlib import Path

from place_platform_v2.admin_drafts import AdminDraftStatus, AdminDraftStore, AdminDraftService
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.create_candidate_resolution_diagnostic import diagnose_approved_create_candidate_resolution
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.sqlite_store import SQLitePlaceRepository


class TestPhase2V31ResolutionDiagnostic(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.canonical=root/"canonical.sqlite3"; self.drafts=root/"drafts.sqlite3"
        with SQLitePlaceRepository(self.canonical): pass

    def tearDown(self): self.tmp.cleanup()

    def _seed(self,name="Caltex Station",lat=14.1200,lon=101.2300,website=None):
        place=CanonicalPlace(identity=PlaceIdentity(),canonical_name=name,location=GeoPoint(lat,lon),province="ปราจีนบุรี",categories=("fuel",),website=website)
        with SQLitePlaceRepository(self.canonical) as repo: repo.save_place(place)
        return place

    def _create(self,name="Caltex Statio",lat=14.1202,lon=101.2302,website=None):
        changes=[
            {"field_name":"canonical_name","value":name},
            {"field_name":"location","value":{"latitude":lat,"longitude":lon}},
            {"field_name":"province","value":"ปราจีนบุรี"},
            {"field_name":"categories","value":["fuel"]},
        ]
        if website is not None: changes.append({"field_name":"website","value":website})
        saved=AdminDraftService(self.canonical,self.drafts).persist({
            "mode":"evidence_draft_only","operation":"create_place_candidate","place_id":None,
            "source":{"source_name":"admin-source","source_url":"https://example.com/candidate"},"changes":changes,
        })
        with AdminDraftStore(self.drafts) as store: store.review(saved.draft_id,AdminDraftStatus.APPROVED)
        return saved

    def test_v311_reports_review_canonical_and_signals(self):
        seeded=self._seed(); draft=self._create()
        result=diagnose_approved_create_candidate_resolution(canonical_database=self.canonical,draft_database=self.drafts,draft_id=draft.draft_id)
        self.assertEqual(result.overall_outcome,"review")
        self.assertEqual(result.review_count,1)
        self.assertEqual(result.comparisons[0].canonical_place_id,seeded.identity.place_id)
        self.assertIn("near_location",result.comparisons[0].signals)
        self.assertIn("similar_name",result.comparisons[0].signals)
        self.assertIsNotNone(result.comparisons[0].distance_m)

    def test_v312_mirrors_matched_semantics(self):
        seeded=self._seed(name="Caltex",lat=14.12,lon=101.23)
        draft=self._create(name="Caltex",lat=14.12,lon=101.23)
        result=diagnose_approved_create_candidate_resolution(canonical_database=self.canonical,draft_database=self.drafts,draft_id=draft.draft_id)
        self.assertEqual(result.overall_outcome,"matched")
        self.assertEqual(result.same_entity_count,1)
        self.assertEqual(result.comparisons[0].canonical_place_id,seeded.identity.place_id)

    def test_v313_new_candidate_has_no_relevant_comparisons(self):
        self._seed(name="Other",lat=13.0,lon=100.0)
        draft=self._create(name="Caltex",lat=14.12,lon=101.23)
        result=diagnose_approved_create_candidate_resolution(canonical_database=self.canonical,draft_database=self.drafts,draft_id=draft.draft_id)
        self.assertEqual(result.overall_outcome,"new")
        self.assertEqual(result.relevant_count,0)

    def test_v314_is_byte_for_byte_read_only(self):
        self._seed(); draft=self._create()
        canonical_before=self.canonical.read_bytes(); drafts_before=self.drafts.read_bytes()
        result=diagnose_approved_create_candidate_resolution(canonical_database=self.canonical,draft_database=self.drafts,draft_id=draft.draft_id)
        self.assertTrue(result.canonical_unchanged)
        self.assertEqual(self.canonical.read_bytes(),canonical_before)
        self.assertEqual(self.drafts.read_bytes(),drafts_before)
        self.assertFalse(result.publication_performed)


if __name__ == "__main__": unittest.main()
