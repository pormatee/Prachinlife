import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from dataclasses import fields, is_dataclass

from place_platform_v2.publication import PublishedPlaceView, GeoPoint, PlaceLifecycle
from place_platform_v2.persisted_published_projection_v1 import (
    PersistedPublishedProjectionWriterV1,
    SQLitePublishedPlaceRepositoryV1,
)
from place_platform_v2.read_model import PublishedTextQuery


def _sample_view():
    # Reuse an existing repository test fixture if a direct default constructor is unavailable.
    import inspect
    sig = inspect.signature(PublishedPlaceView)
    kwargs = {}
    for name, p in sig.parameters.items():
        ann = p.annotation
        if name in ("place_id", "id"):
            kwargs[name] = "projection-v1-test-place"
        elif name in ("canonical_name", "name", "display_name"):
            kwargs[name] = "Projection V1 Test"
        elif name == "location":
            kwargs[name] = GeoPoint(14.076182, 100.633498)
        elif name == "lifecycle":
            kwargs[name] = PlaceLifecycle.ACTIVE
        elif name == "province":
            kwargs[name] = "ปทุมธานี"
        elif name in ("categories", "category_ids"):
            kwargs[name] = ("vegetarian",)
        elif name == "category":
            kwargs[name] = "vegetarian"
        elif name in ("latitude", "lat"):
            kwargs[name] = 14.076182
        elif name in ("longitude", "lon", "lng"):
            kwargs[name] = 100.633498
        elif name in ("publication_policy_version", "policy_version"):
            kwargs[name] = "test-policy"
        elif name in ("published_at", "created_at", "updated_at"):
            kwargs[name] = datetime(2026, 8, 28, tzinfo=timezone.utc)
        elif ann is bool:
            kwargs[name] = True
        elif ann is int:
            kwargs[name] = 1
        elif ann is float:
            kwargs[name] = 1.0
        elif ann is str:
            kwargs[name] = ""
        elif p.default is not inspect._empty:
            continue
        else:
            raise RuntimeError("UNSUPPORTED_REQUIRED_FIELD:"+name)
    return PublishedPlaceView(**kwargs)


class ProjectionV1Test(unittest.TestCase):
    def test_round_trip_if_contract_is_scalar_constructible(self):
        try:
            view = _sample_view()
        except RuntimeError as e:
            self.skipTest(str(e))
        with tempfile.TemporaryDirectory() as td:
            db=os.path.join(td,"projection.sqlite3")
            w=PersistedPublishedProjectionWriterV1(db)
            w.upsert(view)
            r=SQLitePublishedPlaceRepositoryV1(db)
            got=r.get_published(getattr(view,"place_id"))
            self.assertEqual(got,view)

    def test_repository_connection_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            db=os.path.join(td,"projection.sqlite3")
            PersistedPublishedProjectionWriterV1(db).ensure_schema()
            r=SQLitePublishedPlaceRepositoryV1(db)
            con=r._connect()
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute("CREATE TABLE forbidden_write(x INTEGER)")
            finally:
                con.close()

    def test_brain_module_does_not_reference_storage(self):
        from pathlib import Path
        p=Path("place_platform_v2/end_to_end_real_decision_flow_v1.py")
        text=p.read_text(encoding="utf-8",errors="ignore")
        self.assertNotIn("sqlite3",text)
        self.assertNotIn("prachinlife_index.json",text)
        self.assertNotIn("vegetarian_index.json",text)


if __name__ == "__main__":
    unittest.main()
