import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.evidence_acquisition import (
    acquire_osm_contact_evidence,
    build_exact_osm_query,
    build_osm_acquisition_targets,
    parse_osm_target,
)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/v2/place_platform_v2.sqlite3"
PLAN = ROOT / "data/v2/discovery_reports/targeted_production_enrichment_v2.json"


class Phase33EvidenceAcquisitionTests(unittest.TestCase):
    def test_osm_record_parser_accepts_expected_production_ids(self):
        self.assertEqual(parse_osm_target("osm-node-4477017880"), ("node", 4477017880))
        self.assertEqual(parse_osm_target("osm-way-343670272"), ("way", 343670272))
        self.assertIsNone(parse_osm_target("manual-123"))

    def test_top_priority_plan_produces_osm_targets(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        targets = build_osm_acquisition_targets(plan)
        self.assertGreater(len(targets), 0)
        self.assertLessEqual(len(targets), plan["queue_count"])
        query = build_exact_osm_query(targets[:2])
        self.assertIn("out center tags", query)
        self.assertIn(f"{targets[0].osm_type}({targets[0].osm_id});", query)

    def test_matching_exact_osm_object_emits_candidate_contact_evidence_only(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        target = build_osm_acquisition_targets(plan)[0]
        con = sqlite3.connect(DB)
        row = con.execute("SELECT canonical_name,latitude,longitude FROM places WHERE place_id=?", (target.place_id,)).fetchone()
        con.close()
        self.assertIsNotNone(row)
        name, lat, lon = row
        element = {
            "type": target.osm_type,
            "id": target.osm_id,
            "lat": lat,
            "lon": lon,
            "center": {"lat": lat, "lon": lon},
            "tags": {"name": name, "phone": "012345678", "website": "https://example.test/place"},
        }
        with tempfile.TemporaryDirectory() as td:
            small_plan = copy.deepcopy(plan)
            small_plan["queue"] = [next(q for q in plan["queue"] if q["place_id"] == target.place_id)]
            small_plan["queue_count"] = 1
            pp = Path(td) / "plan.json"
            pp.write_text(json.dumps(small_plan, ensure_ascii=False), encoding="utf-8")
            report = acquire_osm_contact_evidence(
                database_path=DB,
                targeted_plan_path=pp,
                fetcher=lambda query: [element],
                observed_at=datetime(2026, 8, 23, tzinfo=timezone.utc),
            )
        self.assertEqual(report["matched_target_count"], 1)
        self.assertEqual(report["candidate_claim_count"], 2)
        self.assertEqual(report["candidate_field_counts"], {"phone": 1, "website": 1})
        self.assertTrue(all(c["status"] == "candidate" for c in report["claims"]))
        self.assertTrue(all(c["source"]["source_type"] == "osm" for c in report["claims"]))
        self.assertTrue(report["safety"]["database_unchanged"])
        self.assertFalse(report["safety"]["evidence_writes"])
        self.assertFalse(report["safety"]["trust_policy_lowered"])

    def test_name_conflict_blocks_contact_claims(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        target = build_osm_acquisition_targets(plan)[0]
        con = sqlite3.connect(DB)
        row = con.execute("SELECT latitude,longitude FROM places WHERE place_id=?", (target.place_id,)).fetchone()
        con.close()
        lat, lon = row
        element = {
            "type": target.osm_type,
            "id": target.osm_id,
            "lat": lat,
            "lon": lon,
            "center": {"lat": lat, "lon": lon},
            "tags": {"name": "Definitely Different Place", "phone": "012345678"},
        }
        with tempfile.TemporaryDirectory() as td:
            small = copy.deepcopy(plan)
            small["queue"] = [next(q for q in plan["queue"] if q["place_id"] == target.place_id)]
            pp = Path(td) / "plan.json"
            pp.write_text(json.dumps(small, ensure_ascii=False), encoding="utf-8")
            report = acquire_osm_contact_evidence(database_path=DB, targeted_plan_path=pp, fetcher=lambda q: [element])
        self.assertEqual(report["candidate_claim_count"], 0)
        self.assertEqual(report["blocked_counts"].get("identity_name_conflict"), 1)

    def test_location_conflict_blocks_contact_claims(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        target = build_osm_acquisition_targets(plan)[0]
        con = sqlite3.connect(DB)
        name = con.execute("SELECT canonical_name FROM places WHERE place_id=?", (target.place_id,)).fetchone()[0]
        con.close()
        element = {
            "type": target.osm_type,
            "id": target.osm_id,
            "lat": 0.0,
            "lon": 0.0,
            "center": {"lat": 0.0, "lon": 0.0},
            "tags": {"name": name, "website": "https://example.test"},
        }
        with tempfile.TemporaryDirectory() as td:
            small = copy.deepcopy(plan)
            small["queue"] = [next(q for q in plan["queue"] if q["place_id"] == target.place_id)]
            pp = Path(td) / "plan.json"
            pp.write_text(json.dumps(small, ensure_ascii=False), encoding="utf-8")
            report = acquire_osm_contact_evidence(database_path=DB, targeted_plan_path=pp, fetcher=lambda q: [element])
        self.assertEqual(report["candidate_claim_count"], 0)
        self.assertEqual(report["blocked_counts"].get("identity_location_conflict_or_missing"), 1)

    def test_no_contact_tags_does_not_invent_evidence(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        target = build_osm_acquisition_targets(plan)[0]
        con = sqlite3.connect(DB)
        name, lat, lon = con.execute("SELECT canonical_name,latitude,longitude FROM places WHERE place_id=?", (target.place_id,)).fetchone()
        con.close()
        element = {"type": target.osm_type, "id": target.osm_id, "lat": lat, "lon": lon, "center": {"lat": lat, "lon": lon}, "tags": {"name": name}}
        with tempfile.TemporaryDirectory() as td:
            small = copy.deepcopy(plan)
            small["queue"] = [next(q for q in plan["queue"] if q["place_id"] == target.place_id)]
            pp = Path(td) / "plan.json"
            pp.write_text(json.dumps(small, ensure_ascii=False), encoding="utf-8")
            report = acquire_osm_contact_evidence(database_path=DB, targeted_plan_path=pp, fetcher=lambda q: [element])
        self.assertEqual(report["candidate_claim_count"], 0)
        self.assertEqual(report["blocked_counts"].get("osm_has_no_missing_contact_tags"), 1)

    def test_source_failure_safe_degrades_without_writes(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        report = acquire_osm_contact_evidence(
            database_path=DB,
            targeted_plan_path=PLAN,
            fetcher=lambda q: (_ for _ in ()).throw(RuntimeError("network down")),
        )
        self.assertFalse(report["source_available"])
        self.assertFalse(report["acquisition_complete"])
        self.assertEqual(report["candidate_claim_count"], 0)
        self.assertTrue(report["safety"]["database_unchanged"])
        self.assertFalse(report["safety"]["evidence_writes"])
        self.assertFalse(report["safety"]["trust_policy_lowered"])



if __name__ == "__main__":
    unittest.main()
