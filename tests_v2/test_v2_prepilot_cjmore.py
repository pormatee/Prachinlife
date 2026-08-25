from pathlib import Path
import unittest

import normalizers.cjmore as cj


ROOT = Path(".")


class TestPrePilotCJMore(unittest.TestCase):

    def test_collector_exists(self):
        self.assertTrue(
            (
                ROOT
                / "collectors"
                / "cjmore.py"
            ).exists()
        )

    def test_normalizer_contract(self):
        item = cj.normalize_record(
            {
                "source_id": "cjmore-test",
                "title": "โปรโมชั่นทดสอบ",
                "image_url": "",
                "destination_url": (
                    "https://www.cjmore.co.th/"
                    "upload/promotion/"
                    "e-book/196/index.html"
                ),
                "source_page": (
                    "https://www.cjmore.co.th/"
                    "promotion"
                ),
                "raw_type": "campaign",
                "collected_at": (
                    "2026-08-25T00:00:00+00:00"
                ),
            }
        )

        self.assertEqual(
            item["merchant"],
            "CJ MORE",
        )
        self.assertEqual(
            item["source"],
            "CJ MORE Official",
        )
        self.assertEqual(
            item["source_type"],
            "official_promotion",
        )
        self.assertTrue(
            item["verified"]
        )
        self.assertEqual(
            item["location_scope"],
            "national",
        )
        self.assertEqual(
            item["country"],
            "TH",
        )

    def test_merge_includes_cjmore(self):
        text = (
            ROOT
            / "scripts"
            / "merge_promotions.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"cjmore.json"',
            text,
        )

    def test_source_health_includes_cjmore(self):
        text = (
            ROOT
            / "scripts"
            / "build_source_health.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"cjmore"',
            text,
        )

    def test_index_has_cjmore_tags(self):
        text = (
            ROOT
            / "scripts"
            / "build_prachinlife_index.py"
        ).read_text(
            encoding="utf-8"
        )

        for marker in (
            '"cjmore"',
            '"ซีเจ"',
            '"ซีเจ มอร์"',
        ):
            self.assertIn(
                marker,
                text,
            )


if __name__ == "__main__":
    unittest.main()
