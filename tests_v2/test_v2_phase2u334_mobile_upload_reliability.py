from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADMIN = (ROOT / 'admin.html').read_text(encoding='utf-8')
ADMIN_JS = (ROOT / 'js/admin/admin.js').read_text(encoding='utf-8')
ADMIN_CSS = (ROOT / 'admin.css').read_text(encoding='utf-8')
SERVER_PATH = ROOT / 'scripts/admin_internal_server.py'

spec = importlib.util.spec_from_file_location('admin_internal_server_u334', SERVER_PATH)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class TestPhase2U334MobileUploadReliability(unittest.TestCase):
    def test_u33401_upload_status_is_visible(self):
        self.assertIn('id="adminImageUploadStatus"', ADMIN)
        self.assertIn('ลองอัปโหลดอีกครั้ง', ADMIN_JS)

    def test_u33402_mobile_mime_is_inferred(self):
        self.assertIn('function inferImageType(', ADMIN_JS)
        self.assertIn('image/jpeg', ADMIN_JS)
        self.assertIn('image/webp', ADMIN_JS)

    def test_u33403_large_mobile_image_has_resize_path(self):
        self.assertIn('prepareMobileImage', ADMIN_JS)
        self.assertIn('createImageBitmap', ADMIN_JS)
        self.assertIn('canvas.toBlob', ADMIN_JS)
        self.assertIn('ย่อรูปอัตโนมัติ', ADMIN_JS)

    def test_u33404_network_retry_and_timeout_exist(self):
        self.assertIn('AbortController', ADMIN_JS)
        self.assertIn('attempt < 2', ADMIN_JS)
        self.assertIn('30000', ADMIN_JS)

    def test_u33405_build_draft_retries_missing_media_reference(self):
        self.assertIn('กำลังลองอัปโหลดรูปอีกครั้งก่อนสร้าง Draft', ADMIN_JS)
        self.assertIn('await uploadSelectedImage()', ADMIN_JS)

    def test_u33406_server_sniffs_mobile_images(self):
        self.assertEqual(server._sniff_image_type(b'\xff\xd8\xffabc', '', 'photo'), 'image/jpeg')
        self.assertEqual(server._sniff_image_type(b'\x89PNG\r\n\x1a\nabc', 'application/octet-stream', 'photo'), 'image/png')
        self.assertEqual(server._sniff_image_type(b'RIFFxxxxWEBPabc', '', 'photo'), 'image/webp')

    def test_u33407_server_decodes_filename(self):
        text = SERVER_PATH.read_text(encoding='utf-8')
        self.assertIn('unquote(', text)
        self.assertIn('_sniff_image_type(', text)
        self.assertIn('"hotfix":"2U.3.3.4"', text)

    def test_u33408_public_safety_boundary_unchanged(self):
        index = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('adminImageUploadStatus', index)
        text = SERVER_PATH.read_text(encoding='utf-8')
        self.assertIn('Canonical writes: DISABLED', text)
        self.assertIn('Publication: DISABLED', text)


if __name__ == '__main__':
    unittest.main()
