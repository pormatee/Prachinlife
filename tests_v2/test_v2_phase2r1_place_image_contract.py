from __future__ import annotations

import unittest
from pathlib import Path


INDEX = Path("index.html")

IMAGE_JS = Path(
    "js/core/place-image.js"
)

MASTER_DIR = Path(
    "assets/images/place-masters"
)


class TestPhase2R1PlaceImageContract(
    unittest.TestCase
):

    def test_r101_contract_exists(
        self
    ):

        self.assertTrue(
            IMAGE_JS.exists()
        )


    def test_r102_master_images_exist(
        self
    ):

        for name in (
            "eat-master.png",
            "cafe-master.png",
            "vegetarian-master.png",
            "go-master.png",
            "service-master.png",
        ):

            self.assertTrue(
                (
                    MASTER_DIR / name
                ).exists(),
                name,
            )


    def test_r103_real_image_candidates(
        self
    ):

        text = IMAGE_JS.read_text(
            encoding="utf-8"
        )

        for marker in (
            "image_url",
            "photo_url",
            "thumbnail_url",
            "metadata",
        ):

            self.assertIn(
                marker,
                text,
            )


    def test_r104_master_fallback(
        self
    ):

        text = IMAGE_JS.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "resolvePlaceImage",
            text,
        )

        self.assertIn(
            'type:\n        "master"',
            text,
        )


    def test_r105_loaded_before_place_modules(
        self
    ):

        text = INDEX.read_text(
            encoding="utf-8"
        )

        image_pos = text.find(
            "js/core/place-image.js"
        )

        vegetarian_pos = text.find(
            "js/modules/vegetarian.js"
        )

        go_pos = text.find(
            "js/modules/go.js"
        )

        service_pos = text.find(
            "js/modules/service.js"
        )

        self.assertGreaterEqual(
            image_pos,
            0,
        )

        self.assertLess(
            image_pos,
            vegetarian_pos,
        )

        self.assertLess(
            image_pos,
            go_pos,
        )

        self.assertLess(
            image_pos,
            service_pos,
        )


    def test_r106_no_production_switch(
        self
    ):

        text = IMAGE_JS.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "publicProduction",
            text,
        )

        self.assertNotIn(
            "public_production",
            text,
        )


if __name__ == "__main__":
    unittest.main()
