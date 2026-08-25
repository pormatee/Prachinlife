from pathlib import Path
import unittest


ROOT = Path(".")
IMAGE_JS = ROOT / "js/core/place-image.js"
STYLE = ROOT / "style.css"
MASTER = ROOT / "assets/images/place-masters"


class TestPrePilotMasterImageV2(unittest.TestCase):

    def test_master_v2_assets_exist(self):
        expected = [
            "eat/eat-01.png",
            "cafe/cafe-01.png",
            "vegetarian/vegetarian-01.png",
            "go/go-01.png",
            "service/pharmacy/pharmacy-01.png",
            "service/clinic/clinic-01.png",
            "service/fuel/fuel-01.png",
            "service/laundry/laundry-01.png",
            "service/car-repair/car-repair-01.png",
            "service/generic/service-01.png",
        ]

        for rel in expected:
            self.assertTrue((MASTER / rel).exists(), rel)

    def test_master_pool_architecture_exists(self):
        text = IMAGE_JS.read_text(encoding="utf-8")

        for marker in (
            "MASTER_POOLS",
            '"service:pharmacy"',
            '"service:clinic"',
            '"service:fuel"',
            '"service:laundry"',
            '"service:car_repair"',
            '"service:generic"',
            "stableHash",
            "getStableSeed",
            "getMasterPoolKey",
        ):
            self.assertIn(marker, text)

    def test_real_image_priority_preserved(self):
        text = IMAGE_JS.read_text(encoding="utf-8")

        self.assertIn("const realImage = getRealImage(place);", text)
        self.assertIn('type: "real"', text)
        self.assertIn('type: "master"', text)

    def test_master_disclosure_exists(self):
        js = IMAGE_JS.read_text(encoding="utf-8")
        css = STYLE.read_text(encoding="utf-8")

        self.assertIn("ภาพประกอบ", js)
        self.assertIn("place-master-badge", js)
        self.assertIn(".place-master-badge", css)

    def test_real_image_failure_reveals_disclosure(self):
        text = IMAGE_JS.read_text(encoding="utf-8")

        self.assertIn("this.dataset.masterImage", text)
        self.assertIn("this.src=this.dataset.masterImage", text)
        self.assertIn("classList.remove('hidden')", text)

    def test_legacy_master_compatibility_preserved(self):
        text = IMAGE_JS.read_text(encoding="utf-8")

        for marker in (
            "eat-master.png",
            "cafe-master.png",
            "vegetarian-master.png",
            "go-master.png",
            "service-master.png",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
