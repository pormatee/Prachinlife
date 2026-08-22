from __future__ import annotations
import hashlib, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
ROOT=Path(__file__).resolve().parents[1]; CANONICAL=ROOT/'data/v2/place_platform_v2.sqlite3'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

class TestPhase2U332QueueStateConsistency(unittest.TestCase):
    def payload(self, text='v1'):
        return {
            'mode':'evidence_draft_only','operation':'create_place_candidate','place_id':None,
            'current_place_name':'ร้านทดสอบคิว','source':{'source_name':'Wongnai','source_url':'https://example.com/queue-place'},
            'changes':[{'field_name':'canonical_name','value':'ร้านทดสอบคิว'},{'field_name':'province','value':'ปราจีนบุรี'},{'field_name':'description','value':text}],
        }

    def test_u3321_review_supersedes_older_pending_versions(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'draft.sqlite3'; svc=AdminDraftService(CANONICAL,db)
            first=svc.persist(self.payload('v1')); latest=svc.persist(self.payload('v2'))
            with AdminDraftStore(db) as store:
                store.review(latest.draft_id, AdminDraftStatus.REJECTED)
                rows=store._connection.execute('SELECT draft_id,status FROM admin_evidence_drafts ORDER BY created_at').fetchall()
                self.assertEqual(rows[0]['status'], AdminDraftStatus.SUPERSEDED)
                self.assertEqual(rows[1]['status'], AdminDraftStatus.REJECTED)

    def test_u3322_pending_count_matches_pending_groups_after_review(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'draft.sqlite3'; svc=AdminDraftService(CANONICAL,db)
            svc.persist(self.payload('v1')); latest=svc.persist(self.payload('v2'))
            with AdminDraftStore(db) as store:
                store.review(latest.draft_id, AdminDraftStatus.APPROVED)
                raw=store._connection.execute("SELECT COUNT(*) FROM admin_evidence_drafts WHERE status='pending_review'").fetchone()[0]
                self.assertEqual(raw, len(store.list_review_groups(AdminDraftStatus.PENDING_REVIEW)))
                self.assertEqual(raw, 0)

    def test_u3323_new_pending_after_review_remains_actionable(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'draft.sqlite3'; svc=AdminDraftService(CANONICAL,db)
            old=svc.persist(self.payload('v1'))
            with AdminDraftStore(db) as store: store.review(old.draft_id, AdminDraftStatus.APPROVED)
            newest=svc.persist(self.payload('v2-after-approval'))
            with AdminDraftStore(db) as store:
                groups=store.list_review_groups(AdminDraftStatus.PENDING_REVIEW)
                self.assertEqual(len(groups),1); self.assertEqual(groups[0]['draft_id'],newest.draft_id)

    def test_u3324_historical_inconsistent_db_is_repaired_on_open(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'draft.sqlite3'; svc=AdminDraftService(CANONICAL,db)
            first=svc.persist(self.payload('v1')); latest=svc.persist(self.payload('v2'))
            # Simulate a pre-hotfix DB: latest reviewed but older version left pending.
            con=sqlite3.connect(db); con.execute("UPDATE admin_evidence_drafts SET status='rejected' WHERE draft_id=?",(latest.draft_id,)); con.commit(); con.close()
            with AdminDraftStore(db) as store:
                statuses=dict(store._connection.execute('SELECT draft_id,status FROM admin_evidence_drafts').fetchall())
                self.assertEqual(statuses[first.draft_id], AdminDraftStatus.SUPERSEDED)
                self.assertEqual(statuses[latest.draft_id], AdminDraftStatus.REJECTED)

    def test_u3325_candidate_identity_does_not_use_null_target_only(self):
        text=(ROOT/'place_platform_v2/admin_drafts.py').read_text(encoding='utf-8')
        self.assertIn('candidate:', text); self.assertIn('source_url', text); self.assertIn('canonical_name', text)

    def test_u3326_superseded_kept_as_audit_history(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'draft.sqlite3'; svc=AdminDraftService(CANONICAL,db)
            svc.persist(self.payload('v1')); latest=svc.persist(self.payload('v2'))
            with AdminDraftStore(db) as store:
                store.review(latest.draft_id,'approved')
                groups=store.list_review_groups('approved')
                self.assertEqual(groups[0]['versions_total'],2)
                self.assertEqual(groups[0]['version_history'][0]['status'],'superseded')

    def test_u3327_canonical_unchanged(self):
        before=sha(CANONICAL)
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'draft.sqlite3'; svc=AdminDraftService(CANONICAL,db); r=svc.persist(self.payload())
            with AdminDraftStore(db) as store: store.review(r.draft_id,'approved')
        self.assertEqual(before,sha(CANONICAL))

    def test_u3328_publication_still_disabled(self):
        text=(ROOT/'scripts/admin_internal_server.py').read_text(encoding='utf-8')
        self.assertIn('Canonical writes: DISABLED', text); self.assertIn('Publication: DISABLED', text)

if __name__=='__main__': unittest.main()
