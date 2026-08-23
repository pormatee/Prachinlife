import json, tempfile, unittest
from pathlib import Path
from place_platform_v2.post_publication_verification import verify_post_publication

FILES=("prachinlife_index.json","vegetarian_index.json","go_index.json","service_index.json")

class T(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        (root/"data/v2/staging/user_web").mkdir(parents=True)
        (root/"data/v2").mkdir(parents=True, exist_ok=True)
        (root/"data/v2/place_platform_v2.sqlite3").write_bytes(b"db")
        for i,n in enumerate(FILES):
            if n=="prachinlife_index.json":
                row={"id":f"{i}-1","content_type":"eat","title":"Eat","location":{"province":"ปราจีนบุรี","latitude":14.0,"longitude":101.0},
                     "metadata":{"contact":{"phone":"+6600000000","website":"https://example.test"}},"source":"x","source_url":"https://src.test"}
            else:
                row={"id":f"{i}-1","title":"Place","content_type":"service","location":{"province":"ปราจีนบุรี","latitude":14.0,"longitude":101.0},
                     "metadata":{"show_in_primary_directory":True,"phone":"+6600000000","website":"https://example.test"},"source":"x","source_url":"https://src.test"}
            rows=[row]
            for p in (root/n, root/"data/v2/staging/user_web"/n):
                p.write_text(json.dumps(rows),encoding="utf-8")
        return td,root

    def test_pass_and_read_only(self):
        td,r=self.fixture(); self.addCleanup(td.cleanup)
        before=(r/"data/v2/place_platform_v2.sqlite3").read_bytes()
        x=verify_post_publication(r)
        self.assertEqual(x["status"],"PASS")
        self.assertTrue(x["safety"]["database_unchanged"])
        self.assertFalse(x["safety"]["production_writes"])
        self.assertEqual(before,(r/"data/v2/place_platform_v2.sqlite3").read_bytes())

    def test_nested_schema_action_readiness_is_nonzero(self):
        td,r=self.fixture(); self.addCleanup(td.cleanup)
        x=verify_post_publication(r)
        self.assertEqual(x["visible_place_count"],4)
        self.assertEqual(x["action_ready"]["map"],4)
        self.assertEqual(x["action_ready"]["phone"],4)
        self.assertEqual(x["action_ready"]["website"],4)
        self.assertTrue(x["safety"]["shared_quality_semantics"])

    def test_detects_staging_contact_drift(self):
        td,r=self.fixture(); self.addCleanup(td.cleanup)
        p=r/"data/v2/staging/user_web/vegetarian_index.json"
        x=json.loads(p.read_text()); x[0]["metadata"]["phone"]="+6699999999"; p.write_text(json.dumps(x))
        z=verify_post_publication(r)
        self.assertEqual(z["status"],"FAIL")
        self.assertEqual(len(z["staging_contact_mismatches"]),1)

    def test_blocks_top_level_preview_marker_in_production(self):
        td,r=self.fixture(); self.addCleanup(td.cleanup)
        p=r/"vegetarian_index.json"
        x=json.loads(p.read_text()); x[0]["v2_preview_overlay"]=True; p.write_text(json.dumps(x))
        z=verify_post_publication(r)
        self.assertEqual(z["status"],"FAIL")
        self.assertEqual(len(z["production_shape_violations"]),1)

if __name__=="__main__":
    unittest.main()
