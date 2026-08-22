from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.admin_media import AdminMediaStore

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / 'data/v2/place_platform_v2.sqlite3'
EXPORT = ROOT / 'data/v2/exports/prachinlife_places_v2.json'


class TestPhase2U331MediaReviewHotfix(unittest.TestCase):
    def test_u3311_server_serves_configured_media_directory(self):
        text = (ROOT / 'scripts/admin_internal_server.py').read_text(encoding='utf-8')
        self.assertIn('def _serve_admin_media', text)
        self.assertIn('self.media_directory / storage_name', text)
        self.assertIn('if self._serve_admin_media(path): return', text)

    def test_u3312_media_url_contract_stays_reviewable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with AdminMediaStore(Path(tmp)/'media.sqlite3', Path(tmp)/'media') as store:
                asset = store.save(data=b'valid-enough-for-store', original_name='photo.png', content_type='image/png')
                self.assertTrue(asset.url.startswith('/data/v2/admin_media/'))
                self.assertTrue((Path(tmp)/'media'/Path(asset.url).name).exists())

    def test_u3313_media_change_persists_to_pending_queue(self):
        place = json.loads(EXPORT.read_text(encoding='utf-8'))['places'][0]
        payload = {
            'schema_version':'2U.3.3.1-v1','intake':'admin_web','mode':'evidence_draft_only',
            'operation':'update_place_candidate','place_id':place['id'],
            'source':{'source_name':'Official','source_url':'https://example.com/source'},
            'changes':[{'field_name':'description','value':'hotfix text'}, {'field_name':'real_image','value':'http://127.0.0.1:8765/data/v2/admin_media/test.png'}],
            'commerce_foundation':{'merchant_content':{},'sponsor_entitlement':{'mode':'normal','auto_expire':True}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp)/'drafts.sqlite3'
            result = AdminDraftService(CANONICAL, db).persist(payload)
            self.assertEqual(result.status, AdminDraftStatus.PENDING_REVIEW)
            with AdminDraftStore(db) as store:
                groups = store.list_review_groups(AdminDraftStatus.PENDING_REVIEW)
            self.assertEqual(len(groups), 1)
            fields = {c['field_name'] for c in groups[0]['payload']['changes']}
            self.assertIn('real_image', fields)
            self.assertIn('description', fields)

    def test_u3314_review_first_version_includes_image_change_summary(self):
        js = (ROOT / 'js/admin/review.js').read_text(encoding='utf-8')
        self.assertIn('imageDiffValue', js)
        self.assertIn('รูปก่อนหน้า', js)
        self.assertIn('รูปที่เสนอ', js)
        self.assertIn('field_name==="real_image"', js)

    def test_u3315_review_image_diff_uses_real_img_elements(self):
        js = (ROOT / 'js/admin/review.js').read_text(encoding='utf-8')
        self.assertIn('admin-image-diff-figure', js)
        self.assertIn('<img src=', js)
        self.assertIn('admin-image-diff-pair', js)

    def test_u3316_mobile_image_diff_css_exists(self):
        css = (ROOT / 'admin.css').read_text(encoding='utf-8')
        self.assertIn('.admin-image-diff-pair', css)
        self.assertIn('.admin-image-diff-figure img', css)
        self.assertIn('@media (max-width: 720px)', css)

    def test_u3317_admin_cache_bust_updated(self):
        admin = (ROOT / 'admin.html').read_text(encoding='utf-8')
        review = (ROOT / 'admin-review.html').read_text(encoding='utf-8')
        self.assertIn('phase2u331-20260822', admin)
        self.assertIn('phase2u331-20260822', review)

    def test_u3318_still_no_canonical_or_publication_write(self):
        server = (ROOT / 'scripts/admin_internal_server.py').read_text(encoding='utf-8')
        self.assertIn('Canonical writes: DISABLED', server)
        self.assertIn('Publication: DISABLED', server)
        self.assertNotIn('commit_adoption(', server)


if __name__ == '__main__':
    unittest.main()
