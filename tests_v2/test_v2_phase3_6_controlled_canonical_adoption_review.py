import json
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.canonical_adoption_review import review_controlled_canonical_adoption
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.sqlite_store import SQLitePlaceRepository

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)


class TestPhase36CanonicalAdoptionReview(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.db = Path(self.t.name) / "db.sqlite3"
        repo = SQLitePlaceRepository(self.db)
        self.pid = str(uuid.uuid4())
        repo.save_place(CanonicalPlace(
            identity=PlaceIdentity(self.pid), canonical_name="Test", location=GeoPoint(13,100),
            province="กรุงเทพมหานคร", categories=("eat",), lifecycle=PlaceLifecycle.ACTIVE,
            created_at=NOW, updated_at=NOW,
        ))
        repo.close()

    def tearDown(self): self.t.cleanup()

    def add_ev(self, field, value, source, status="supported", marker=True):
        con=sqlite3.connect(self.db)
        eid=str(uuid.uuid4())
        meta={"persistence":"phase3_5_controlled_web_evidence"} if marker else {}
        con.execute("""INSERT INTO place_evidence(
          evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,
          kind,field_name,value_json,status,observed_at,metadata_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
          eid,self.pid,"web",source,source,"https://example.com/"+source,NOW.isoformat(),"contact",field,
          json.dumps(value),status,NOW.isoformat(),json.dumps(meta)
        ))
        con.commit(); con.close(); return eid

    def test_supported_phone_is_proposed_under_existing_policy(self):
        self.add_ev("phone","021234567","A")
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertEqual(r["review_place_field_count"],1)
        self.assertEqual(r["adoption_outcome_counts"],{"proposed":1})
        self.assertEqual(r["decisions"][0]["verification_outcome"],"supported")

    def test_two_sources_are_verified_and_proposed(self):
        self.add_ev("phone","021234567","A","verified")
        self.add_ev("phone","021234567","B","verified")
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertEqual(r["verification_outcome_counts"],{"verified":1})
        self.assertEqual(r["adoption_outcome_counts"],{"proposed":1})

    def test_conflict_from_any_active_evidence_blocks_adoption(self):
        self.add_ev("phone","021234567","A")
        self.add_ev("phone","029999999","B",marker=False)
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertEqual(r["verification_outcome_counts"],{"conflicting":1})
        self.assertEqual(r["adoption_outcome_counts"],{"blocked":1})

    def test_existing_same_canonical_value_is_no_change(self):
        con=sqlite3.connect(self.db); con.execute("update places set phone=? where place_id=?",("021234567",self.pid)); con.commit(); con.close()
        self.add_ev("phone","021234567","A")
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertEqual(r["adoption_outcome_counts"],{"no_change":1})

    def test_review_is_read_only(self):
        self.add_ev("website","https://official.example","A")
        before=self.db.read_bytes()
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertTrue(r["safety"]["database_unchanged"])
        self.assertFalse(r["safety"]["automatic_adoption"])

    def test_non_phase35_evidence_does_not_expand_scope(self):
        self.add_ev("phone","021234567","A",marker=False)
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertEqual(r["review_place_field_count"],0)

    def test_province_agnostic_guard(self):
        self.add_ev("phone","021234567","A")
        r=review_controlled_canonical_adoption(database_path=self.db)
        self.assertTrue(r["safety"]["province_agnostic"])
        self.assertFalse(r["safety"]["trust_policy_lowered"])


if __name__ == "__main__": unittest.main()
