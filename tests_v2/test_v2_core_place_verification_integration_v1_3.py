from __future__ import annotations
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import place_platform_v2.core_place_verification_compat as compat


class CorePlaceVerificationIntegrationV13Test(unittest.TestCase):

    def test_real_report_name_supported(self):
        self.assertIn(
            "pathum_coordinate_acquisition_v1.json",
            compat.COORDINATE_REPORT_NAMES,
        )

    def test_default_report_root_is_independent_of_database_location(self):
        source = Path(compat.__file__).read_text(encoding="utf-8")
        self.assertIn(
            'root = Path(__file__).resolve().parents[1]',
            source,
        )
        self.assertNotIn(
            'root = db.resolve().parents[2]',
            source,
        )

    def test_loader_understands_real_pathum_shape(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pathum_coordinate_acquisition_v1.json"
            p.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "candidate_key": "vg",
                                "name": "Vegan Garden ร้านอาหารเจ-มังสวิรัติ คาเฟ่",
                                "province": "ปทุมธานี",
                                "coordinate_outcome": "EXACT_COORDINATES_VERIFIED",
                            },
                            {
                                "candidate_key": "sv",
                                "name": "Vegetarian by So Vegan ไอยรา",
                                "province": "ปทุมธานี",
                                "coordinate_outcome": "EXACT_COORDINATES_VERIFIED",
                            },
                            {
                                "candidate_key": "bj",
                                "name": "Baan J Veggie House",
                                "province": "ปทุมธานี",
                                "coordinate_outcome": "EXACT_COORDINATES_UNRESOLVED",
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            by_key, by_np = compat._load_coordinate_results([p])
            self.assertEqual(
                "EXACT_COORDINATES_VERIFIED",
                by_np[("Vegan Garden ร้านอาหารเจ-มังสวิรัติ คาเฟ่", "ปทุมธานี")],
            )
            self.assertEqual(
                "EXACT_COORDINATES_VERIFIED",
                by_np[("Vegetarian by So Vegan ไอยรา", "ปทุมธานี")],
            )
            self.assertEqual(
                "EXACT_COORDINATES_UNRESOLVED",
                by_np[("Baan J Veggie House", "ปทุมธานี")],
            )


if __name__ == "__main__":
    unittest.main()
