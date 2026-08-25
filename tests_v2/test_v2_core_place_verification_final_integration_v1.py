from __future__ import annotations
import unittest
from pathlib import Path

import place_platform_v2.controlled_new_place_adoption_core_v2 as core_adopt
import place_platform_v2.core_place_verification_compat as compat

class CoreV2FinalIntegrationContractTest(unittest.TestCase):

    def test_real_pathum_coordinate_report_supported(self):
        self.assertIn(
            "pathum_coordinate_acquisition_v1.json",
            compat.COORDINATE_REPORT_NAMES,
        )

    def test_core_v2_adoption_is_separate_from_legacy_machine(self):
        legacy = Path("place_platform_v2/new_place_adoption_machine.py").read_text(encoding="utf-8")
        self.assertNotIn("controlled_new_place_adoption_core_v2", legacy)

    def test_coordinate_pending_shell_policy_is_explicit(self):
        source = Path(core_adopt.__file__).read_text(encoding="utf-8")
        self.assertIn("READY_CANONICAL_COORDINATE_PENDING", source)
        self.assertIn("coordinate_pending_canonical_shell_has_null_coordinates", source)
        self.assertIn("near_me_requires_exact_coordinates", source)

    def test_no_automatic_publication_contract(self):
        source = Path(core_adopt.__file__).read_text(encoding="utf-8")
        self.assertIn('"automatic_publication": False', source)
        self.assertIn('"automatic_canonical_adoption": False', source)
        self.assertIn('"explicit_commit_required": True', source)

if __name__ == "__main__":
    unittest.main()
