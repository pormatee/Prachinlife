from __future__ import annotations

import unittest
from pathlib import Path


APP = Path("app.js")
INDEX = Path("index.html")

IMAGE = Path(
    "js/core/place-image.js"
)

VEG = Path(
    "js/modules/vegetarian.js"
)

GO = Path(
    "js/modules/go.js"
)

SERVICE = Path(
    "js/modules/service.js"
)


class TestPhase2R2RendererImages(
    unittest.TestCase
):

    def test_r201_shared_renderer_exists(
        self
    ):

        text = IMAGE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "function renderPlaceImage(",
            text,
        )

        self.assertIn(
            "data-place-image-type",
            text,
        )

        self.assertIn(
            "data-master-image",
            text,
        )


    def test_r202_real_to_master_onerror(
        self
    ):

        text = IMAGE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "this.dataset.masterImage",
            text,
        )

        self.assertIn(
            "this.src=this.dataset.masterImage",
            text,
        )


    def test_r203_eat_uses_shared_image(
        self
    ):

        text = APP.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "placeImage.renderPlaceImage(",
            text,
        )

        self.assertNotIn(
            "${icon}",
            text[
                text.find("function renderEatCard("):
                text.find(
                    "/* =====================================================\nEAT HELPERS"
                )
            ],
        )


    def test_r204_vegetarian_uses_shared_image(
        self
    ):

        text = VEG.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "placeImage.renderPlaceImage(",
            text,
        )

        self.assertNotIn(
            "image-placeholder eat-placeholder",
            text,
        )


    def test_r205_go_uses_shared_image(
        self
    ):

        text = GO.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "placeImage.renderPlaceImage(",
            text,
        )

        self.assertNotIn(
            "image-placeholder eat-placeholder",
            text,
        )


    def test_r206_service_uses_shared_image(
        self
    ):

        text = SERVICE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "placeImage.renderPlaceImage(",
            text,
        )

        self.assertNotIn(
            "image-placeholder eat-placeholder",
            text,
        )


    def test_r207_cache_bust(
        self
    ):

        text = INDEX.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "js/core/place-image.js?v=",
            text,
        )

        self.assertIn(
            "app.js?v=",
            text,
        )


    def test_r208_v2_runtime_preserved(
        self
    ):

        text = APP.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "PrachinLifeV2Runtime",
            text,
        )

        self.assertIn(
            "getEatDatasetV2First",
            text,
        )


if __name__ == "__main__":
    unittest.main()
