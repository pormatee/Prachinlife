import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
import inspect
from pathlib import Path

from place_platform_v2.publication import PublishedPlaceView, GeoPoint, PlaceLifecycle
from place_platform_v2.persisted_published_projection_v1 import (
    PersistedPublishedProjectionWriterV1,
    SQLitePublishedPlaceRepositoryV1,
)
from place_platform_v2.read_model import PublishedTextQuery, PublishedNearbyQuery


def make_view(place_id, name, province="ปทุมธานี", category="vegetarian", lat=14.076182, lon=100.633498):
    sig = inspect.signature(PublishedPlaceView)
    kwargs = {}
    for pname, p in sig.parameters.items():
        ann = p.annotation
        if pname in ("place_id", "id"):
            kwargs[pname] = place_id
        elif pname in ("canonical_name", "name", "display_name"):
            kwargs[pname] = name
        elif pname == "location":
            kwargs[pname] = GeoPoint(lat, lon)
        elif pname == "lifecycle":
            kwargs[pname] = PlaceLifecycle.ACTIVE
        elif pname == "province":
            kwargs[pname] = province
        elif pname in ("categories", "category_ids"):
            kwargs[pname] = (category,)
        elif pname == "category":
            kwargs[pname] = category
        elif pname in ("latitude", "lat"):
            kwargs[pname] = lat
        elif pname in ("longitude", "lon", "lng"):
            kwargs[pname] = lon
        elif pname in ("publication_policy_version", "policy_version"):
            kwargs[pname] = "challenge-policy"
        elif pname in ("published_at", "created_at", "updated_at"):
            kwargs[pname] = datetime(2026, 8, 28, tzinfo=timezone.utc)
        elif ann is bool:
            kwargs[pname] = True
        elif ann is int:
            kwargs[pname] = 1
        elif ann is float:
            kwargs[pname] = 1.0
        elif ann is str:
            kwargs[pname] = ""
        elif p.default is not inspect._empty:
            continue
        else:
            raise RuntimeError("UNSUPPORTED_REQUIRED_FIELD:"+pname)
    return PublishedPlaceView(**kwargs)


def q_text(text="", province=None, categories=(), limit=50):
    return PublishedTextQuery(text=text, province=province, categories=categories, limit=limit)


class ProjectionChallenge(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.td.name, "projection.sqlite3")
        self.writer = PersistedPublishedProjectionWriterV1(self.db)
        try:
            self.a = make_view("a","Baan J Veggie House","ปทุมธานี","vegetarian",14.076182,100.633498)
            self.b = make_view("b","Vegan Garden","ปทุมธานี","vegetarian",14.090000,100.640000)
            self.c = make_view("c","Other Province","ชลบุรี","vegetarian",13.300000,100.900000)
            self.d = make_view("d","Service Place","ปทุมธานี","service",14.077000,100.634000)
        except RuntimeError as e:
            self.skipTest(str(e))
        for v in (self.a,self.b,self.c,self.d):
            self.writer.upsert(v)
        self.repo = SQLitePublishedPlaceRepositoryV1(self.db)

    def tearDown(self):
        self.td.cleanup()

    def test_exact_round_trip(self):
        self.assertEqual(self.repo.get_published("a"), self.a)

    def test_missing_id_returns_none(self):
        self.assertIsNone(self.repo.get_published("missing"))

    def test_province_isolation(self):
        got=self.repo.search_text(q_text(province="ปทุมธานี"))
        self.assertTrue(got)
        self.assertTrue(all(getattr(v,"province",None)=="ปทุมธานี" for v in got))

    def test_category_isolation(self):
        got=self.repo.search_text(q_text(province="ปทุมธานี",categories=("vegetarian",)))
        ids={getattr(v,"place_id") for v in got}
        self.assertNotIn("d",ids)

    def test_limit_respected(self):
        got=self.repo.search_text(q_text(province="ปทุมธานี",limit=1))
        self.assertEqual(len(got),1)

    def test_text_search_no_cross_province_leak(self):
        got=self.repo.search_text(q_text(text="Other Province",province="ปทุมธานี"))
        self.assertEqual(got, ())

    def test_wrong_projection_schema_version_is_hidden(self):
        con=sqlite3.connect(self.db)
        try:
            con.execute("update decision_published_places_v1 set projection_schema_version='WRONG' where place_id='a'")
            con.commit()
        finally:
            con.close()
        self.assertIsNone(self.repo.get_published("a"))

    def test_corrupt_payload_fails_closed(self):
        con=sqlite3.connect(self.db)
        try:
            con.execute("update decision_published_places_v1 set payload_json='not-json' where place_id='a'")
            con.commit()
        finally:
            con.close()
        with self.assertRaises(Exception):
            self.repo.get_published("a")

    def test_reader_cannot_write(self):
        con=self.repo._connect()
        try:
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("delete from decision_published_places_v1")
        finally:
            con.close()

    def test_writer_remove_is_not_reader_authority(self):
        self.assertFalse(hasattr(self.repo,"remove"))
        self.assertFalse(hasattr(self.repo,"upsert"))

    def test_brain_has_no_storage_import(self):
        text=Path("place_platform_v2/end_to_end_real_decision_flow_v1.py").read_text(encoding="utf-8",errors="ignore")
        self.assertNotIn("sqlite3",text)
        self.assertNotIn("persisted_published_projection_v1",text)
        self.assertNotIn("prachinlife_index.json",text)
        self.assertNotIn("vegetarian_index.json",text)

    def test_adapter_has_no_json_index_dependency(self):
        text=Path("place_platform_v2/persisted_published_projection_v1.py").read_text(encoding="utf-8",errors="ignore")
        self.assertNotIn("prachinlife_index.json",text)
        self.assertNotIn("vegetarian_index.json",text)

    def test_table_has_projection_only_columns(self):
        con=sqlite3.connect(f"file:{Path(self.db).resolve()}?mode=ro",uri=True)
        try:
            cols=[r[1] for r in con.execute("pragma table_info(decision_published_places_v1)")]
        finally:
            con.close()
        self.assertEqual(cols,[
            "place_id","province","categories_json","latitude","longitude",
            "payload_json","projection_schema_version"
        ])


if __name__ == "__main__":
    unittest.main()
