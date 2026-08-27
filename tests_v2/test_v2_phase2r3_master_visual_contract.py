from __future__ import annotations
import hashlib
import unittest
from pathlib import Path
import struct

ROOT = Path('.')
MASTER_DIR = ROOT / 'assets/images/place-masters'
STYLE = ROOT / 'style.css'
INDEX = ROOT / 'index.html'
ADAPTER = ROOT / 'js/core/v2-place-adapter.js'

class TestPhase2R3MasterVisualContract(unittest.TestCase):
    def test_r301_landscape_master_assets(self):
        names = [
            'eat-master.png','cafe-master.png','vegetarian-master.png',
            'go-master.png','service-master.png'
        ]
        for name in names:
            p=MASTER_DIR/name
            self.assertTrue(p.exists(), name)
            data = p.read_bytes()
            self.assertTrue(
                data.startswith(b"\x89PNG\r\n\x1a\n"),
                name,
            )
            self.assertGreaterEqual(len(data), 24, name)
            width, height = struct.unpack(
                ">II",
                data[16:24],
            )
            self.assertGreaterEqual(width, 1000, name)
            self.assertGreaterEqual(height, 600, name)
            self.assertAlmostEqual(
                width / height,
                16 / 10,
                delta=0.02,
                msg=name,
            )

    def test_r302_master_assets_are_not_duplicates(self):
        hashes=[]
        for p in sorted(MASTER_DIR.glob('*-master.png')):
            hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertGreaterEqual(len(hashes), 5)
        self.assertEqual(len(hashes), len(set(hashes)))

    def test_r303_shared_place_image_css(self):
        text=STYLE.read_text(encoding='utf-8')
        self.assertIn('.place-card-image', text)
        self.assertIn('[data-place-image-type="master"]', text)
        self.assertIn('.eat-image-wrap', text)
        self.assertIn('aspect-ratio: 16 / 9', text)

    def test_r304_adapter_preserves_future_real_image(self):
        text=ADAPTER.read_text(encoding='utf-8')
        self.assertIn('text(place.image_url)', text)
        self.assertIn('text(place.photo_url)', text)
        self.assertIn('text(place.thumbnail_url)', text)

    def test_r305_cache_bust(self):
        text=INDEX.read_text(encoding='utf-8')
        self.assertIn('phase10p1-20260823', text)
        self.assertIn('baanj-user-web-v1-4-20260826', text)

if __name__ == '__main__':
    unittest.main()
