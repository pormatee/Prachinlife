from __future__ import annotations
import unittest
from place_platform_v2.province_category_pipeline import (
    ProvinceCategoryPipeline, PublicState, Scope
)

class GenericProvinceCategoryPipelineTests(unittest.TestCase):
    def setUp(self):
        self.p = ProvinceCategoryPipeline()

    def test_verified_public_allows_near_me_and_distance(self):
        d = self.p.classify(
            Scope("ปทุมธานี", "vegetarian"),
            dict(
                ready_for_publication=True,
                verified=True,
                human_confirmation_required=False,
                human_confirmation_complete=False,
                public_limited_eligible=False,
                latitude=14.0,
                longitude=100.5,
            ),
        )
        self.assertEqual(d.state, PublicState.VERIFIED_PUBLIC)
        self.assertTrue(d.public_visible)
        self.assertTrue(d.near_me_allowed)
        self.assertTrue(d.distance_allowed)

    def test_pending_human_public_limited_blocks_near_me_and_distance(self):
        d = self.p.classify(
            Scope("เชียงใหม่", "cafe"),
            dict(
                ready_for_publication=False,
                verified=False,
                human_confirmation_required=True,
                human_confirmation_complete=False,
                public_limited_eligible=True,
                latitude=18.7,
                longitude=98.9,
            ),
        )
        self.assertEqual(d.state, PublicState.PENDING_HUMAN_PUBLIC_LIMITED)
        self.assertTrue(d.public_visible)
        self.assertFalse(d.near_me_allowed)
        self.assertFalse(d.distance_allowed)

    def test_hidden_not_ready_fail_closed(self):
        d = self.p.classify(Scope("ชลบุรี", "service"), {})
        self.assertEqual(d.state, PublicState.HIDDEN_NOT_READY)
        self.assertFalse(d.public_visible)
        self.assertFalse(d.near_me_allowed)
        self.assertFalse(d.distance_allowed)

    def test_generic_across_provinces_and_categories(self):
        for province in ("ปทุมธานี","ปราจีนบุรี","กรุงเทพมหานคร","ภูเก็ต"):
            for category in ("vegetarian","eat","go","service","cafe"):
                d = self.p.classify(
                    Scope(province, category),
                    dict(
                        ready_for_publication=True,
                        verified=True,
                        human_confirmation_required=False,
                        public_limited_eligible=False,
                        latitude=13.5,
                        longitude=100.5,
                    ),
                )
                self.assertEqual(d.scope.province, province)
                self.assertEqual(d.scope.category, category)
                self.assertEqual(d.state, PublicState.VERIFIED_PUBLIC)

    def test_no_automatic_actions_or_trust_lowering(self):
        for record in (
            {},
            dict(public_limited_eligible=True,
                 human_confirmation_required=True,
                 human_confirmation_complete=False),
            dict(ready_for_publication=True, verified=True,
                 human_confirmation_required=False,
                 latitude=1, longitude=1),
        ):
            d = self.p.classify(Scope("ขอนแก่น","eat"), record)
            self.assertFalse(d.automatic_canonical)
            self.assertFalse(d.automatic_approval)
            self.assertFalse(d.automatic_publication)
            self.assertFalse(d.trust_policy_lowered)

if __name__ == "__main__":
    unittest.main()
