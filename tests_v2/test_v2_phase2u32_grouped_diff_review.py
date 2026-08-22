from __future__ import annotations
import hashlib, tempfile, unittest
from pathlib import Path
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
ROOT=Path(__file__).resolve().parents[1]; CANONICAL=ROOT/'data/v2/place_platform_v2.sqlite3'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
class TestPhase2U32GroupedDiffReview(unittest.TestCase):
    def create_payload(self, description, phone=None):
        changes=[{'field_name':'canonical_name','value':'ร้านทดสอบเวอร์ชัน'},{'field_name':'province','value':'ปราจีนบุรี'},{'field_name':'description','value':description}]
        if phone is not None: changes.append({'field_name':'phone','value':phone})
        return {'mode':'evidence_draft_only','operation':'create_place_candidate','place_id':None,'current_place_name':'ร้านทดสอบเวอร์ชัน','source':{'source_name':'Test Source','source_url':'https://example.com/place/1'},'changes':changes}
    def test_u321_same_place_is_one_review_group(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; svc=AdminDraftService(CANONICAL,db); a=svc.persist(self.create_payload('v1')); b=svc.persist(self.create_payload('v2','0800000000'))
            self.assertNotEqual(a.draft_id,b.draft_id)
            with AdminDraftStore(db) as store:
                groups=store.list_review_groups(); self.assertEqual(len(groups),1); self.assertEqual(groups[0]['versions_total'],2); self.assertEqual(groups[0]['draft_id'],b.draft_id)
    def test_u322_diff_marks_added_and_changed(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; svc=AdminDraftService(CANONICAL,db); svc.persist(self.create_payload('v1')); svc.persist(self.create_payload('v2','0800000000'))
            with AdminDraftStore(db) as store:
                diff={x['field_name']:x for x in store.list_review_groups()[0]['version_diff']}
                self.assertEqual(diff['description']['kind'],'changed'); self.assertEqual(diff['phone']['kind'],'added')
    def test_u323_history_keeps_both_versions(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; svc=AdminDraftService(CANONICAL,db); svc.persist(self.create_payload('v1')); svc.persist(self.create_payload('v2'))
            with AdminDraftStore(db) as store:
                history=store.list_review_groups()[0]['version_history']; self.assertEqual([x['version'] for x in history],[1,2])
    def test_u324_only_latest_version_can_review(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; svc=AdminDraftService(CANONICAL,db); first=svc.persist(self.create_payload('v1')); latest=svc.persist(self.create_payload('v2'))
            with AdminDraftStore(db) as store:
                with self.assertRaisesRegex(ValueError,'latest draft version'): store.review(first.draft_id,'approved')
                self.assertEqual(store.review(latest.draft_id,'approved')['review_status'],'approved')
    def test_u325_group_filter_follows_latest_status(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; svc=AdminDraftService(CANONICAL,db); svc.persist(self.create_payload('v1')); latest=svc.persist(self.create_payload('v2'))
            with AdminDraftStore(db) as store:
                store.review(latest.draft_id,'approved'); self.assertEqual(len(store.list_review_groups('pending_review')),0); self.assertEqual(len(store.list_review_groups('approved')),1)
    def test_u326_review_ui_has_diff_and_history(self):
        text=(ROOT/'js/admin/review.js').read_text(encoding='utf-8'); self.assertIn('version_diff',text); self.assertIn('สิ่งที่เปลี่ยนจากเวอร์ชันก่อนหน้า',text); self.assertIn('version_history',text)
    def test_u327_server_uses_grouped_queue(self):
        text=(ROOT/'scripts/admin_internal_server.py').read_text(encoding='utf-8'); self.assertIn('list_review_groups',text); self.assertRegex(text,r'2U\.3\.(?:2|3)')
    def test_u328_mobile_diff_is_responsive(self):
        css=(ROOT/'admin.css').read_text(encoding='utf-8'); self.assertIn('.admin-diff-row',css); self.assertIn('@media(max-width:760px)',css)
    def test_u329_no_canonical_change(self):
        before=sha(CANONICAL)
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; svc=AdminDraftService(CANONICAL,db); latest=svc.persist(self.create_payload('v1')); AdminDraftStore(db).close();
            with AdminDraftStore(db) as store: store.review(latest.draft_id,AdminDraftStatus.APPROVED)
        self.assertEqual(before,sha(CANONICAL))
    def test_u3210_publication_still_disabled(self):
        text=(ROOT/'scripts/admin_internal_server.py').read_text(encoding='utf-8'); self.assertIn('Canonical writes: DISABLED',text); self.assertIn('Publication: DISABLED',text)
if __name__=='__main__': unittest.main()
