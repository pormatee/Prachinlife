from __future__ import annotations
import tempfile
import unittest
import json
from pathlib import Path
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore

ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/'admin.css').read_text(encoding='utf-8')
PREVIEW=(ROOT/'js/admin/preview.js').read_text(encoding='utf-8')
ADMIN=(ROOT/'admin.html').read_text(encoding='utf-8')
REVIEW=(ROOT/'admin-review.html').read_text(encoding='utf-8')

class TestPhase2U31MobilePreviewHotfix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical=ROOT/'data/v2/place_platform_v2.sqlite3'
        cls.place=json.loads((ROOT/'data/v2/exports/prachinlife_places_v2.json').read_text(encoding='utf-8'))['places'][0]
    def test_u311_mobile_review_is_bounded(self):
        for marker in ('overflow-x:hidden','max-width:100%','.admin-review-card{overflow:hidden}', '.admin-review-table-wrap{max-width:100%'):
            self.assertIn(marker,CSS)
    def test_u312_preview_exposes_added_fields(self):
        for marker in ('admin-preview-detail-grid','อำเภอ','ตำบล','โทรศัพท์','เว็บไซต์','รายละเอียด'):
            self.assertIn(marker,PREVIEW)
    def test_u313_mobile_preview_stacks(self):
        self.assertIn('@media(max-width:760px)',CSS)
        self.assertIn('.admin-before-after-preview{grid-template-columns:1fr}',CSS)
    def test_u314_cache_bust(self):
        self.assertRegex(ADMIN, r'phase2u3(?:1|3|31)-20260822')
        self.assertRegex(REVIEW, r'phase2u3(?:1|2|31)-20260822')
    def test_u315_duplicate_pending_guard_exists(self):
        text=(ROOT/'place_platform_v2/admin_drafts.py').read_text(encoding='utf-8')
        self.assertIn('find_pending_duplicate',text)
        self.assertIn('if duplicate is not None',text)
    def test_u316_no_canonical_publish_enable(self):
        combined=CSS+PREVIEW+ADMIN+REVIEW
        self.assertNotIn('canonical_write = True',combined)
        self.assertNotIn('publication = True',combined)
    def test_u317_identical_pending_submit_is_idempotent(self):
        payload={
            'mode':'evidence_draft_only','operation':'update_place_candidate','place_id':self.place['id'],
            'source':{'source_name':'OpenStreetMap','source_url':'https://www.openstreetmap.org/'},
            'note':'double tap','changes':[{'field_name':'description','value':'same draft'}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'drafts.sqlite3'
            service=AdminDraftService(self.canonical,db)
            first=service.persist(payload); second=service.persist(payload)
            self.assertEqual(first.draft_id,second.draft_id)
            with AdminDraftStore(db) as store:
                self.assertEqual(store.count(),1)

if __name__=='__main__': unittest.main()
