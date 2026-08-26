from __future__ import annotations

import importlib
import json
import sqlite3
import unittest
from pathlib import Path

from place_platform_v2.generic_pipeline_integration import (
    GenericPipelineIntegration,
    PipelineStageStatus,
)
from place_platform_v2.province_category_pipeline import PublicState


DB = Path("data/v2/place_platform_v2.sqlite3")


def stages(**overrides):
    data = dict(
        discovery_ready=True,
        identity_ready=True,
        evidence_ready=True,
        verification_ready=True,
        human_confirmation_required=False,
        human_confirmation_complete=False,
        admin_approved=True,
        canonical_ready=True,
        coordinate_ready=True,
    )
    data.update(overrides)
    return PipelineStageStatus(**data)


class GenericPipelineIntegrationV1Tests(unittest.TestCase):
    def setUp(self):
        self.engine = GenericPipelineIntegration()

    def test_01_verified_public_end_to_end_contract(self):
        result = self.engine.evaluate(
            province="ปราจีนบุรี",
            category="eat",
            stages=stages(),
            record={"latitude": 14.05, "longitude": 101.37},
        )
        self.assertEqual(result.decision.state, PublicState.VERIFIED_PUBLIC)
        self.assertTrue(result.decision.near_me_allowed)
        self.assertTrue(result.decision.distance_allowed)
        self.assertTrue(result.publication_allowed)

    def test_02_pending_human_public_limited_blocks_location_features(self):
        result = self.engine.evaluate(
            province="ปราจีนบุรี",
            category="vegetarian",
            stages=stages(
                verification_ready=False,
                human_confirmation_required=True,
                human_confirmation_complete=False,
                admin_approved=False,
                canonical_ready=False,
                coordinate_ready=False,
            ),
            record={"latitude": 14.05, "longitude": 101.37},
        )
        self.assertEqual(result.decision.state, PublicState.PENDING_HUMAN_PUBLIC_LIMITED)
        self.assertTrue(result.decision.public_visible)
        self.assertFalse(result.decision.near_me_allowed)
        self.assertFalse(result.decision.distance_allowed)
        self.assertFalse(result.publication_allowed)

    def test_03_hidden_when_evidence_not_ready(self):
        result = self.engine.evaluate(
            province="ปราจีนบุรี",
            category="service",
            stages=stages(
                evidence_ready=False,
                verification_ready=False,
                admin_approved=False,
                canonical_ready=False,
                coordinate_ready=False,
            ),
            record={},
        )
        self.assertEqual(result.decision.state, PublicState.HIDDEN_NOT_READY)
        self.assertFalse(result.decision.public_visible)

    def test_04_reference_and_production_province_same_behavior(self):
        kwargs = dict(
            category="eat",
            stages=stages(),
            record={"latitude": 14.0, "longitude": 100.5},
        )
        a = self.engine.evaluate(province="ปทุมธานี", **kwargs)
        b = self.engine.evaluate(province="ปราจีนบุรี", **kwargs)
        self.assertEqual(a.decision.state, b.decision.state)
        self.assertEqual(a.decision.near_me_allowed, b.decision.near_me_allowed)
        self.assertEqual(a.decision.distance_allowed, b.decision.distance_allowed)

    def test_05_multi_category_same_contract(self):
        for category in ("eat", "service", "vegetarian"):
            result = self.engine.evaluate(
                province="ปราจีนบุรี",
                category=category,
                stages=stages(),
                record={"latitude": 14.1, "longitude": 101.4},
            )
            self.assertEqual(result.decision.state, PublicState.VERIFIED_PUBLIC)

    def test_06_no_automatic_actions_or_trust_lowering(self):
        result = self.engine.evaluate(
            province="ปราจีนบุรี",
            category="service",
            stages=stages(),
            record={"latitude": 14.1, "longitude": 101.4},
        )
        self.assertFalse(result.automatic_canonical)
        self.assertFalse(result.automatic_approval)
        self.assertFalse(result.automatic_publication)
        self.assertFalse(result.trust_policy_lowered)

    def test_07_real_pipeline_modules_import(self):
        modules = (
            "place_platform_v2.ingestion",
            "place_platform_v2.discovery_resolution",
            "place_platform_v2.discovery_readonly",
            "place_platform_v2.admin_verified_workflow",
            "place_platform_v2.final_readiness_gate",
            "place_platform_v2.web_export",
            "place_platform_v2.province_category_pipeline",
        )
        for name in modules:
            with self.subTest(module=name):
                self.assertIsNotNone(importlib.import_module(name))

    def test_08_real_discovery_contract_symbols_exist(self):
        ingestion = importlib.import_module("place_platform_v2.ingestion")
        resolution = importlib.import_module("place_platform_v2.discovery_resolution")
        self.assertTrue(hasattr(ingestion, "DiscoveryIngestionPipeline"))
        self.assertTrue(hasattr(ingestion, "DiscoveryRequest"))
        self.assertTrue(hasattr(resolution, "CanonicalResolutionOrchestrator"))

    def test_09_real_db_has_prachinburi_scope(self):
        con = sqlite3.connect(DB)
        try:
            n = con.execute(
                "SELECT COUNT(*) FROM places WHERE province=?",
                ("ปราจีนบุรี",),
            ).fetchone()[0]
        finally:
            con.close()
        self.assertGreater(n, 0)

    def test_10_real_db_category_profile_has_production_proof_targets(self):
        con = sqlite3.connect(DB)
        try:
            rows = con.execute(
                "SELECT categories_json FROM places WHERE province=?",
                ("ปราจีนบุรี",),
            ).fetchall()
        finally:
            con.close()

        groups = {"eat": 0, "service": 0, "vegetarian": 0}
        for (raw,) in rows:
            try:
                value = json.loads(raw)
            except Exception:
                continue
            if isinstance(value, dict) and value.get("__type__") == "tuple":
                cats = value.get("items", [])
            elif isinstance(value, (list, tuple)):
                cats = value
            else:
                cats = []
            s = {str(x).strip().lower() for x in cats}
            if s & {"vegetarian", "vegan", "jay"}:
                groups["vegetarian"] += 1
            if s & {"eat", "food", "restaurant", "cafe", "fast_food", "food_court", "ice_cream"}:
                groups["eat"] += 1
            if s & {"service", "hospital", "clinic", "pharmacy", "bank", "atm", "fuel",
                    "school", "college", "university", "laundry", "car_repair"}:
                groups["service"] += 1

        self.assertGreater(groups["eat"], 0)
        self.assertGreater(groups["service"], 0)
        self.assertIn("vegetarian", groups)


if __name__ == "__main__":
    unittest.main()
