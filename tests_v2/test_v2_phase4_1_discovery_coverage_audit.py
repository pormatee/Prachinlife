import json,sqlite3,tempfile,unittest
from pathlib import Path
from place_platform_v2.discovery_coverage_audit import audit_discovery_coverage
class T(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory(); p=Path(td.name)/"x.sqlite3"
        c=sqlite3.connect(p)
        c.execute("""create table places(place_id text,canonical_name text,province text,categories_json text,latitude real,longitude real,phone text,website text,lifecycle text)""")
        rows=[
          ("1","A","P1",'["eat"]',1,2,None,None,"active"),
          ("2","B","P1",'["eat"]',1,2,None,None,"active"),
          ("3","C","P2",'["vegetarian"]',1,2,"1",None,"active"),
        ]
        c.executemany("insert into places values(?,?,?,?,?,?,?,?,?)",rows);c.commit();c.close()
        return td,p
    def test_read_only_and_counts(self):
        td,p=self.fixture();self.addCleanup(td.cleanup)
        b=p.read_bytes();r=audit_discovery_coverage(p)
        self.assertEqual(r["status"],"PASS");self.assertEqual(r["canonical_place_count"],3)
        self.assertEqual(r["province_count"],2);self.assertEqual(r["category_totals"]["eat"],2)
        self.assertEqual(b,p.read_bytes());self.assertTrue(r["safety"]["database_unchanged"])
    def test_missing_categories_become_discovery_targets(self):
        td,p=self.fixture();self.addCleanup(td.cleanup)
        r=audit_discovery_coverage(p)
        q={(x["province"],x["category"]):x for x in r["coverage_priority_queue"]}
        self.assertEqual(q[("P1","vegetarian")]["gap_kind"],"missing")
        self.assertEqual(q[("P1","service")]["next_step"],"discover_new_places")
    def test_province_agnostic(self):
        td,p=self.fixture();self.addCleanup(td.cleanup)
        r=audit_discovery_coverage(p);self.assertTrue(r["safety"]["province_agnostic"])
        self.assertIn("P2",r["province_coverage"])
    def test_optional_focus_prioritizes_current_launch_province(self):
        td,p=self.fixture();self.addCleanup(td.cleanup)
        r=audit_discovery_coverage(p, focus_province="P1")
        self.assertEqual(r["coverage_priority_queue"][0]["province"],"P1")
        self.assertEqual(r["interpretation"]["focus_province"],"P1")
    def test_does_not_claim_real_world_completeness(self):
        td,p=self.fixture();self.addCleanup(td.cleanup)
        r=audit_discovery_coverage(p)
        self.assertTrue(r["interpretation"]["not_a_real_world_completeness_claim"])
if __name__=="__main__":unittest.main()
