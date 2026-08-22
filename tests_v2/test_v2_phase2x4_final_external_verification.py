import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.external_verification import (
    EXTERNAL_POLICY_VERSION,
    commit_external_verifications,
)
from place_platform_v2.staged_milestone import eligible_place_ids

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/v2/place_platform_v2.sqlite3"
MANIFEST = ROOT / "data/v2/final_blocked_external_sources.json"


class TestFinalExternalVerification(unittest.TestCase):
    def setUp(self):
        self.records = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def _copy_db(self, td):
        db = Path(td) / "copy.sqlite3"
        shutil.copy2(DB, db)
        return db

    def _rewind_external_verification(self, db):
        con = sqlite3.connect(db)
        try:
            with con:
                con.execute(
                    "delete from staged_existence_observations where policy_version=?",
                    (EXTERNAL_POLICY_VERSION,),
                )
                con.execute(
                    "delete from place_evidence where json_extract(metadata_json,'$.policy_version')=?",
                    (EXTERNAL_POLICY_VERSION,),
                )
                rows = con.execute(
                    "select evidence_id,metadata_json from place_evidence "
                    "where status='stale' and json_extract(metadata_json,'$.resolution_policy_version')=?",
                    (EXTERNAL_POLICY_VERSION,),
                ).fetchall()
                for evidence_id, metadata_json in rows:
                    md = json.loads(metadata_json or "{}")
                    for key in (
                        "superseded_by_evidence_id",
                        "superseded_reason",
                        "resolution_policy_version",
                    ):
                        md.pop(key, None)
                    con.execute(
                        "update place_evidence set status='candidate',metadata_json=? where evidence_id=?",
                        (json.dumps(md, ensure_ascii=False, sort_keys=True), evidence_id),
                    )
        finally:
            con.close()

    def test_manifest_covers_precommit_final_blocked_set(self):
        with tempfile.TemporaryDirectory() as td:
            db = self._copy_db(td)
            self._rewind_external_verification(db)
            _, blocked = eligible_place_ids(db)
            blocked_ids = {x["place_id"] for x in blocked}
            manifest_ids = {x["place_id"] for x in self.records}
            self.assertEqual(blocked_ids, manifest_ids)

    def test_commit_makes_all_places_eligible_without_canonical_writes(self):
        with tempfile.TemporaryDirectory() as td:
            db = self._copy_db(td)
            self._rewind_external_verification(db)
            con = sqlite3.connect(db)
            try:
                before_places = con.execute(
                    "select place_id,canonical_name,latitude,longitude,province,categories_json,lifecycle "
                    "from places order by place_id"
                ).fetchall()
            finally:
                con.close()
            committed = commit_external_verifications(db, self.records)
            eligible, blocked = eligible_place_ids(db)
            con = sqlite3.connect(db)
            try:
                after_places = con.execute(
                    "select place_id,canonical_name,latitude,longitude,province,categories_json,lifecycle "
                    "from places order by place_id"
                ).fetchall()
            finally:
                con.close()
            self.assertEqual(len(committed), 5)
            self.assertEqual(len(eligible), 220)
            self.assertEqual(blocked, [])
            self.assertEqual(before_places, after_places)

    def test_commit_is_idempotent_for_same_observed_at(self):
        records = [dict(x, observed_at="2026-08-22T15:00:00+00:00") for x in self.records]
        with tempfile.TemporaryDirectory() as td:
            db = self._copy_db(td)
            self._rewind_external_verification(db)
            first = commit_external_verifications(db, records)
            second = commit_external_verifications(db, records)
            self.assertEqual(len(first), 5)
            self.assertEqual(second, [])

    def test_verona_gets_matching_category_support_from_official_source(self):
        verona = next(x for x in self.records if x["canonical_name"] == "Verona")
        with tempfile.TemporaryDirectory() as td:
            db = self._copy_db(td)
            self._rewind_external_verification(db)
            commit_external_verifications(db, [verona])
            con = sqlite3.connect(db)
            try:
                row = con.execute(
                    "select source_type,source_url,value_json,status from place_evidence "
                    "where place_id=? and field_name='categories' and source_name=? order by observed_at desc limit 1",
                    (verona["place_id"], verona["source_name"]),
                ).fetchone()
            finally:
                con.close()
            self.assertEqual(row[0], "official")
            self.assertEqual(row[1], verona["source_url"])
            self.assertIn('"attraction"', row[2])
            self.assertIn('"restaurant"', row[2])
            self.assertEqual(row[3], "supported")


if __name__ == "__main__":
    unittest.main()
