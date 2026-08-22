from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
ROOT=Path(__file__).resolve().parents[1]; CANONICAL=ROOT/'data/v2/place_platform_v2.sqlite3'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
class TestPhase2U2ReviewQueue(unittest.TestCase):
    def payload(self):
        import sqlite3
        con=sqlite3.connect(CANONICAL); pid=con.execute('select place_id from places limit 1').fetchone()[0]; con.close()
        return {'mode':'evidence_draft_only','operation':'update_place_candidate','place_id':pid,'source':{'source_name':'OpenStreetMap','source_url':'https://www.openstreetmap.org/'},'changes':[{'field_name':'description','value':'ทดสอบ review'}]}
    def test_u201_review_page_exists(self): self.assertTrue((ROOT/'admin-review.html').exists())
    def test_u202_review_page_has_approve_reject(self):
        t=(ROOT/'js/admin/review.js').read_text(); self.assertIn('approved',t); self.assertIn('rejected',t); self.assertIn('previous_value',t)
    def test_u203_pending_can_be_approved(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; r=AdminDraftService(CANONICAL,db).persist(self.payload())
            with AdminDraftStore(db) as s:
                out=s.review(r.draft_id,AdminDraftStatus.APPROVED,'ok'); self.assertEqual(out['review_status'],'approved'); self.assertEqual(len(s.list_for_review('approved')),1)
    def test_u204_pending_can_be_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; r=AdminDraftService(CANONICAL,db).persist(self.payload())
            with AdminDraftStore(db) as s: self.assertEqual(s.review(r.draft_id,'rejected','bad')['review_status'],'rejected')
    def test_u205_review_is_one_way(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; r=AdminDraftService(CANONICAL,db).persist(self.payload())
            with AdminDraftStore(db) as s:
                s.review(r.draft_id,'approved');
                with self.assertRaisesRegex(ValueError,'already reviewed'): s.review(r.draft_id,'rejected')
    def test_u206_review_does_not_change_canonical_db(self):
        before=sha(CANONICAL)
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; r=AdminDraftService(CANONICAL,db).persist(self.payload()); AdminDraftStore(db).close()
            with AdminDraftStore(db) as s: s.review(r.draft_id,'approved')
        self.assertEqual(before,sha(CANONICAL))
    def test_u207_server_disables_canonical_and_publication(self):
        t=(ROOT/'scripts/admin_internal_server.py').read_text(); self.assertIn('Canonical writes: DISABLED',t); self.assertIn('Publication: DISABLED',t); self.assertNotIn('commit_adoption(',t)
    def test_u208_admin_links_review_queue_and_renames_reset(self):
        t=(ROOT/'admin.html').read_text(); self.assertIn('admin-review.html',t); self.assertIn('ยกเลิกการแก้ไข',t); self.assertNotIn('คืนค่าฟอร์ม',t)
    def test_u209_public_index_has_no_review_controls(self):
        t=(ROOT/'index.html').read_text(); self.assertNotIn('admin-review.html',t); self.assertNotIn('data-review-decision',t)
    def test_u210_review_payload_keeps_evidence_and_source(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'d.sqlite3'; AdminDraftService(CANONICAL,db).persist(self.payload())
            with AdminDraftStore(db) as s:
                item=s.list_for_review()[0]; self.assertTrue(item['evidence']); self.assertEqual(item['source_name'],'OpenStreetMap'); self.assertEqual(item['status'],'pending_review')
if __name__=='__main__': unittest.main()
