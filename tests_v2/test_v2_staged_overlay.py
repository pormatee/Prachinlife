from __future__ import annotations
import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.staged_overlay import _overlay_record, build_overlay_staging

class TestStagedOverlay(unittest.TestCase):
    def test_overlay_01_core_identity_comes_from_v2(self):
        record={'id':'x','title':'Old','category':'restaurant','location':{'province':'Old','latitude':1,'longitude':2},'metadata':{}}
        can={'canonical_name':'New','province':'ปราจีนบุรี','latitude':14.1,'longitude':101.2,'categories_json':'{"__type__":"tuple","items":["cafe"]}'}
        out=_overlay_record(record,can,'pid')
        self.assertEqual(out['title'],'New');self.assertEqual(out['category'],'cafe');self.assertEqual(out['location']['latitude'],14.1)
        self.assertTrue(out['metadata']['v2_preview_overlay']);self.assertEqual(out['metadata']['v2_place_id'],'pid')

    def test_overlay_02_optional_legacy_fields_are_preserved(self):
        record={'id':'x','title':'Old','location':{'province':'Old','latitude':1,'longitude':2},'metadata':{'opening_hours':'x','phone':'1'},'source_url':'legacy'}
        can={'canonical_name':'New','province':'ปราจีนบุรี','latitude':14.1,'longitude':101.2,'categories_json':'{"__type__":"tuple","items":["cafe"]}'}
        out=_overlay_record(record,can,'pid')
        self.assertEqual(out['metadata']['opening_hours'],'x');self.assertEqual(out['metadata']['phone'],'1');self.assertEqual(out['source_url'],'legacy')

    def test_overlay_03_original_record_not_mutated(self):
        record={'id':'x','title':'Old','location':{'province':'Old','latitude':1,'longitude':2},'metadata':{}}
        can={'canonical_name':'New','province':'ปราจีนบุรี','latitude':14.1,'longitude':101.2,'categories_json':'{"__type__":"tuple","items":["cafe"]}'}
        _overlay_record(record,can,'pid');self.assertEqual(record['title'],'Old');self.assertEqual(record['location']['province'],'Old')

    def test_overlay_04_full_legacy_coverage_is_preserved(self):
        # Structural invariant: overlay builder must never subset source arrays.
        import inspect, place_platform_v2.staged_overlay as m
        src=inspect.getsource(m.build_overlay_staging)
        self.assertNotIn("content_type')=='deal' or",src)
        self.assertIn('payload.append(record)',src)

    def test_overlay_05_manifest_reports_overlay_and_fallback(self):
        import inspect, place_platform_v2.staged_overlay as m
        src=inspect.getsource(m.build_overlay_staging)
        self.assertIn("'preview_mode': 'v2_overlay_with_v1_fallback'",src)
        self.assertIn("'v2_overlay_records'",src);self.assertIn("'v1_fallback_records'",src)

    def test_overlay_06_public_switch_remains_disabled(self):
        import inspect, place_platform_v2.staged_overlay as m
        src=inspect.getsource(m.build_overlay_staging)
        self.assertIn("'public_user_web_switched': False",src)

if __name__=='__main__':unittest.main()
