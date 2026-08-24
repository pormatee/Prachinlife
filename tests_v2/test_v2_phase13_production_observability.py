from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.phase13_production_observability import (
    DETAIL_FIELDS,
    assert_healthy,
    database_counts,
    detail_coverage,
)

class Phase13ProductionObservabilityTest(unittest.TestCase):
    def test_1301_detail_coverage_counts_fields(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"x.json"
            p.write_text(json.dumps({
                "places":[
                    {"address":"A","phone":""},
                    {"address":"","phone":"1"},
                ]
            }), encoding="utf-8")
            c = detail_coverage(p)
            self.assertEqual(c["places"], 2)
            self.assertEqual(c["address"], 1)
            self.assertEqual(c["phone"], 1)

    def test_1302_detail_fields_include_real_image(self):
        self.assertIn("real_image", DETAIL_FIELDS)
        self.assertIn("description", DETAIL_FIELDS)

    def test_1303_database_counts_readonly(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.sqlite3"
            con=sqlite3.connect(p)
            con.execute("create table places(id text)")
            con.execute("insert into places values('a')")
            con.commit(); con.close()
            self.assertEqual(database_counts(p)["places"], 1)

    def _report(self):
        return {
            "all_public_match_staging": True,
            "detail_coverage": {
                "places":220,
                **{f:0 for f in DETAIL_FIELDS},
            },
            "public_files": {},
            "switch":{
                "status":"SWITCHED",
                "rollback_available":True,
                "public_user_web_switched":True,
                "database_changed":False,
            },
        }

    def test_1304_healthy_switch_passes(self):
        self.assertTrue(assert_healthy(self._report()))

    def test_1305_public_drift_fails_closed(self):
        r=self._report()
        r["all_public_match_staging"]=False
        with self.assertRaises(RuntimeError):
            assert_healthy(r)

    def test_1306_rollback_unavailable_fails_closed(self):
        r=self._report()
        r["switch"]["rollback_available"]=False
        with self.assertRaises(RuntimeError):
            assert_healthy(r)

    def test_1307_coverage_regression_fails_closed(self):
        r=self._report()
        r["detail_coverage"]["phone"]=4
        baseline={"detail_coverage":{"phone":5}}
        with self.assertRaises(RuntimeError):
            assert_healthy(r, baseline)

    def test_1308_place_count_must_remain_220(self):
        r=self._report()
        r["detail_coverage"]["places"]=219
        with self.assertRaises(RuntimeError):
            assert_healthy(r)

if __name__ == "__main__":
    unittest.main()
