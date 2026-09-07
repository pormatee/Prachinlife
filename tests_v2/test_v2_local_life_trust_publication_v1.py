from __future__ import annotations

import os
import unittest

from place_platform_v2.local_life_trust_policy_v1 import (
    ENV_FLAG,
    evaluate_place_like,
    evaluate_release_integrity,
    policy_enabled,
)


class TestLocalLifeTrustPublicationV1(unittest.TestCase):
    def tearDown(self):
        os.environ.pop(ENV_FLAG, None)

    def base_place(self, **kw):
        d = {
            "place_id": "p1",
            "latitude": 14.0,
            "longitude": 101.0,
            "categories_json": '["vegetarian"]',
            "lifecycle": "unknown",
        }
        d.update(kw)
        return d

    def test_unknown_lifecycle_is_visible_with_reasonable_evidence(self):
        d = evaluate_place_like(
            self.base_place(),
            ["no recent explicit existence observation"],
            evidence_count=1,
        )
        self.assertTrue(d.visible)
        self.assertIn("no recent explicit existence observation", d.disclosures)
        self.assertEqual(d.field_trust["existence"], "SUPPORTED")

    def test_closed_is_hard_block(self):
        d = evaluate_place_like(self.base_place(lifecycle="closed"), (), evidence_count=3)
        self.assertFalse(d.visible)

    def test_missing_location_is_hard_block(self):
        d = evaluate_place_like(
            self.base_place(latitude=None, longitude=None), (), evidence_count=1
        )
        self.assertFalse(d.visible)
        self.assertIn("usable location missing", d.hard_blockers)

    def test_missing_category_is_hard_block(self):
        d = evaluate_place_like(
            self.base_place(categories_json="[]"), (), evidence_count=1
        )
        self.assertFalse(d.visible)
        self.assertIn("minimum category missing", d.hard_blockers)

    def test_unsupported_web_verification_is_disclosure(self):
        d = evaluate_place_like(
            self.base_place(),
            ["categories unsupported", "location unsupported"],
            evidence_count=1,
        )
        self.assertTrue(d.visible)
        self.assertEqual(d.field_trust["category"], "SUPPORTED")
        self.assertEqual(d.field_trust["location"], "SUPPORTED")

    def test_strong_negative_evidence_dominates(self):
        d = evaluate_place_like(
            self.base_place(),
            ["recent negative existence/lifecycle evidence"],
            evidence_count=4,
        )
        self.assertFalse(d.visible)

    def test_release_integrity_ignores_legacy_only_blocker(self):
        report = {
            "rollback_verified": True,
            "eligible_place_count": 221,
            "overlay_place_count": 221,
            "unmapped_eligible_place_count": 0,
            "blockers": ["manifest_overlay_mode: legacy preview wording"],
            "checks": {
                "manifest_eligible_overlay_equal": True,
                "manifest_unmapped_zero": True,
                "overlay_unique_place_count": True,
                "overlay_core_identity_matches_v2": True,
                "category_shape_preserved": True,
                "rollback_default_v1_paths_present": True,
            },
        }
        r = evaluate_release_integrity(report)
        self.assertTrue(r.ok)
        self.assertTrue(r.compatibility_warnings)

    def test_release_integrity_keeps_rollback_hard(self):
        report = {
            "rollback_verified": False,
            "eligible_place_count": 221,
            "overlay_place_count": 221,
            "unmapped_eligible_place_count": 0,
            "checks": {},
        }
        self.assertFalse(evaluate_release_integrity(report).ok)

    def test_feature_flag_is_opt_in(self):
        os.environ.pop(ENV_FLAG, None)
        self.assertFalse(policy_enabled())
        os.environ[ENV_FLAG] = "1"
        self.assertTrue(policy_enabled())


if __name__ == "__main__":
    unittest.main()
