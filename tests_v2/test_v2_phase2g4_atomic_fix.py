from __future__ import annotations
import json, unittest
from pathlib import Path
from place_platform_v2.web_export import _decode_categories

EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")
ADAPTER = Path("js/core/v2-place-adapter.js")

class TestPhase2G4AtomicFix(unittest.TestCase):
    def test_decode_typed_tuple(self):
        self.assertEqual(
            _decode_categories('{"__type__":"tuple","items":["restaurant","cafe"]}'),
            ["restaurant","cafe"],
        )

    def test_export_categories_are_lists(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        self.assertTrue(payload["places"])
        for place in payload["places"]:
            self.assertIsInstance(place["categories"], list)

    def test_real_tokens_present(self):
        payload = json.loads(EXPORT.read_text(encoding="utf-8"))
        tokens = {x for p in payload["places"] for x in p["categories"]}
        for token in ("restaurant","cafe","fuel","temple"):
            self.assertIn(token, tokens)

    def test_adapter_maps_real_tokens(self):
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("CATEGORY_ALIASES", text)
        for token in ('"restaurant"','"cafe"','"fuel"','"temple"','"attraction"'):
            self.assertIn(token, text)

if __name__ == "__main__":
    unittest.main()
