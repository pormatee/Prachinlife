import json, sqlite3, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"data/v2/decision_published_places_v1.sqlite3"
EXP=ROOT/"data/v2/exports/decision_published_places_v1.json"
AD=ROOT/"js/core/v2-place-adapter.js"
ABC=["299de6ab-cb79-52f6-ab47-aceb98c18fb8","a9ead1ee-2036-5511-a523-5ab4bcfb607a","4f1af15f-8b4a-55fa-a663-77a288f0b831"]
class TestAlignmentV14(unittest.TestCase):
    def payload(self):
        return json.loads(EXP.read_text(encoding="utf-8"))
    def test_authority_count_identity(self):
        p=self.payload()
        self.assertEqual(p["authority"],"decision_published_places_v1")
        con=sqlite3.connect(f"file:{DB.resolve()}?mode=ro",uri=True)
        try:
            ids={r[0] for r in con.execute("select place_id from decision_published_places_v1")}
        finally:
            con.close()
        self.assertEqual({x["id"] for x in p["places"]},ids)
        self.assertEqual(p["count"],len(ids))
    def test_names_and_typed_payload(self):
        d={x["id"]:x for x in self.payload()["places"]}
        self.assertTrue(all(str(x["name"]).strip() for x in d.values()))
        self.assertEqual(d["0045b5d3-9654-5e3c-b56b-4ee811ba97aa"]["name"],"ร้านน้องเจ")
    def test_abc_resolvable(self):
        ids={x["id"] for x in self.payload()["places"]}
        self.assertTrue(all(x in ids for x in ABC))
    def test_coordinate_pairs_are_atomic(self):
        for place in self.payload()["places"]:
            lat=place["latitude"]
            lon=place["longitude"]
            self.assertEqual(lat is None, lon is None)
            if lat is not None:
                self.assertIsInstance(lat,(int,float))
                self.assertIsInstance(lon,(int,float))
    def test_adapter_contract(self):
        s=AD.read_text(encoding="utf-8")
        self.assertIn('const V2_URL = "data/v2/exports/decision_published_places_v1.json";',s)
        self.assertIn("prachinlife-published-projection-web-1",s)
        self.assertIn("publishedProjectionPlace",s)
if __name__=="__main__":
    unittest.main()
