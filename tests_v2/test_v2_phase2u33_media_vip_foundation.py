from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from place_platform_v2.admin_media import AdminMediaStore, MAX_UPLOAD_BYTES
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore
import json
from place_platform_v2.merchant_foundation import MerchantContentDraft, MerchantMode, SponsorEntitlement

ROOT=Path(__file__).resolve().parents[1]
CANONICAL=ROOT/'data/v2/place_platform_v2.sqlite3'

class TestPhase2U33MediaVipFoundation(unittest.TestCase):
    def test_u331_media_upload_is_separate_from_canonical(self):
        before=hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            with AdminMediaStore(Path(tmp)/'media.sqlite3',Path(tmp)/'media') as store:
                asset=store.save(data=b'fake-png',original_name='shop.png',content_type='image/png')
                self.assertTrue(asset.url.endswith('.png'))
                self.assertTrue((Path(tmp)/'media'/Path(asset.url).name).exists())
        self.assertEqual(hashlib.sha256(CANONICAL.read_bytes()).hexdigest(),before)

    def test_u332_media_rejects_unsupported_and_large_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with AdminMediaStore(Path(tmp)/'m.sqlite3',Path(tmp)/'media') as store:
                with self.assertRaises(ValueError): store.save(data=b'x',original_name='x.gif',content_type='image/gif')
                with self.assertRaises(ValueError): store.save(data=b'x'*(MAX_UPLOAD_BYTES+1),original_name='x.png',content_type='image/png')

    def test_u333_vip_is_time_bound_and_auto_expires(self):
        start=datetime(2026,1,1,tzinfo=timezone.utc); end=datetime(2027,1,1,tzinfo=timezone.utc)
        e=SponsorEntitlement('p1',MerchantMode.VIP,'annual',start,end,True)
        self.assertEqual(e.effective_mode(start+timedelta(days=10)),MerchantMode.VIP)
        self.assertEqual(e.effective_mode(end+timedelta(seconds=1)),MerchantMode.NORMAL)

    def test_u334_future_vip_is_normal_until_contract_starts(self):
        now=datetime.now(timezone.utc); e=SponsorEntitlement('p1',MerchantMode.VIP,'annual',now+timedelta(days=10),now+timedelta(days=375),True)
        self.assertEqual(e.effective_mode(now),MerchantMode.NORMAL)

    def test_u335_invalid_vip_contract_is_rejected(self):
        now=datetime.now(timezone.utc)
        with self.assertRaises(ValueError): SponsorEntitlement('p1',MerchantMode.VIP,'annual',now,now-timedelta(days=1),True)
        with self.assertRaises(ValueError): SponsorEntitlement('p1',MerchantMode.VIP)

    def test_u336_merchant_content_is_separate_and_gallery_bounded(self):
        c=MerchantContentDraft.create(place_id='p1',gallery_media_ids=['a','a','b'],line_url='https://line.me/x')
        self.assertEqual(c.gallery_media_ids,('a','b'))
        with self.assertRaises(ValueError): MerchantContentDraft.create(place_id='p1',gallery_media_ids=[str(i) for i in range(21)])

    def test_u337_admin_form_has_upload_and_vip_foundation_hooks(self):
        html=(ROOT/'admin.html').read_text(encoding='utf-8')
        self.assertIn('id="fieldRealImageUpload"',html)
        self.assertIn('id="adminUploadImageBtn"',html)
        self.assertIn('id="merchantMode"',html)
        self.assertIn('id="vipContractStart"',html)
        self.assertIn('id="vipContractEnd"',html)
        self.assertIn('id="merchantGallery"',html)

    def test_u338_admin_js_uploads_binary_and_previews_uploaded_url(self):
        js=(ROOT/'js/admin/admin.js').read_text(encoding='utf-8')
        self.assertIn('MEDIA_API_URL = "/api/admin/media"',js)
        self.assertIn('body: file',js)
        self.assertIn('fieldRealImage',js)
        self.assertIn('renderLiveImagePreview',js)

    def test_u339_internal_server_has_media_endpoint_and_no_canonical_write(self):
        text=(ROOT/'scripts/admin_internal_server.py').read_text(encoding='utf-8')
        self.assertIn('/api/admin/media',text)
        self.assertIn('AdminMediaStore',text)
        self.assertIn('Canonical writes: DISABLED',text)
        self.assertNotIn('commit_adoption(',text)

    def test_u340_public_runtime_does_not_load_vip_admin_foundation(self):
        text=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertNotIn('/api/admin/media',text)
        self.assertNotIn('vipContractStart',text)

    def test_u341_draft_service_validates_and_preserves_vip_foundation(self):
        place=json.loads((ROOT/'data/v2/exports/prachinlife_places_v2.json').read_text(encoding='utf-8'))['places'][0]
        start=datetime(2026,8,22,tzinfo=timezone.utc); end=datetime(2027,8,22,tzinfo=timezone.utc)
        payload={
            'schema_version':'2U.3.3-v1','intake':'admin_web','mode':'evidence_draft_only',
            'operation':'update_place_candidate','place_id':place['id'],
            'source':{'source_name':'Official','source_url':'https://example.com/source'},
            'changes':[{'field_name':'description','value':'VIP foundation test'}],
            'commerce_foundation':{
                'merchant_content':{'gallery_media_ids':['m1','m2'],'line_url':'https://line.me/test'},
                'sponsor_entitlement':{'mode':'vip','plan':'annual','contract_start_at':start.isoformat(),'contract_end_at':end.isoformat(),'auto_expire':True}
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'drafts.sqlite3'; result=AdminDraftService(CANONICAL,db).persist(payload)
            with AdminDraftStore(db) as store:
                saved=store.list_for_review()[0]['payload']['commerce_foundation']
            self.assertEqual(result.status,'pending_review')
            self.assertEqual(saved['sponsor_entitlement']['mode'],'vip')
            self.assertFalse(saved['public_effect']); self.assertFalse(saved['ranking_effect'])

    def test_u342_invalid_vip_foundation_is_rejected_server_side(self):
        place=json.loads((ROOT/'data/v2/exports/prachinlife_places_v2.json').read_text(encoding='utf-8'))['places'][0]
        payload={'schema_version':'2U.3.3-v1','intake':'admin_web','mode':'evidence_draft_only','operation':'update_place_candidate','place_id':place['id'],'source':{'source_name':'Official','source_url':'https://example.com/source'},'changes':[{'field_name':'description','value':'x'}],'commerce_foundation':{'merchant_content':{},'sponsor_entitlement':{'mode':'vip'}}}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'VIP mode requires'):
                AdminDraftService(CANONICAL,Path(tmp)/'drafts.sqlite3').persist(payload)

if __name__=='__main__': unittest.main()
