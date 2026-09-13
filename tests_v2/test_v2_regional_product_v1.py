import copy
import json
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.regional_product_v1 import (
    CONTRACT_VERSION,
    RegionalProductContractError,
    RegionalProductNotFoundError,
    RegionalProductRegistryV1,
    RegionalProductV1,
    load_regional_product_v1,
)

ROOT = Path(__file__).resolve().parents[1]
PRACHIN = ROOT / "regional_products" / "prachinburi" / "product.json"
SECOND = ROOT / "tests_v2" / "fixtures" / "regional_product_second_region.json"


def valid_payload():
    return json.loads(PRACHIN.read_text(encoding="utf-8"))


class TestV2RegionalProductV1(unittest.TestCase):
    def test_01_prachinlife_declaration_loads(self):
        product = load_regional_product_v1(PRACHIN)
        self.assertEqual(product.contract_version, CONTRACT_VERSION)
        self.assertEqual(product.product_id, "th-prachinburi")
        self.assertEqual(product.region.slug, "prachinburi")
        self.assertEqual(product.region.code, "TH-25")

    def test_02_governance_is_fail_closed_and_read_only(self):
        product = load_regional_product_v1(PRACHIN)
        self.assertTrue(product.governance["fail_closed"])
        self.assertTrue(product.governance["human_final_decision"])
        self.assertFalse(product.governance["direct_canonical_write"])
        self.assertFalse(product.governance["direct_published_write"])

    def test_03_direct_canonical_write_cannot_be_enabled(self):
        payload = valid_payload()
        payload["governance"]["direct_canonical_write"] = True
        with self.assertRaises(RegionalProductContractError):
            RegionalProductV1.from_mapping(payload)

    def test_04_missing_required_key_fails_closed(self):
        payload = valid_payload()
        del payload["region"]["code"]
        with self.assertRaises(RegionalProductContractError):
            RegionalProductV1.from_mapping(payload)

    def test_05_unknown_contract_key_fails_closed(self):
        payload = valid_payload()
        payload["regional_magic"] = True
        with self.assertRaises(RegionalProductContractError):
            RegionalProductV1.from_mapping(payload)

    def test_06_capability_values_must_be_boolean(self):
        payload = valid_payload()
        payload["capabilities"]["near_me"] = "yes"
        with self.assertRaises(RegionalProductContractError):
            RegionalProductV1.from_mapping(payload)

    def test_07_unsafe_config_path_is_rejected(self):
        payload = valid_payload()
        payload["config_refs"]["web"] = "../prachinburi/web.json"
        with self.assertRaises(RegionalProductContractError):
            RegionalProductV1.from_mapping(payload)

    def test_08_second_region_fixture_uses_same_contract(self):
        product = load_regional_product_v1(SECOND)
        self.assertEqual(product.product_id, "th-reference-sandbox")
        self.assertEqual(product.region.slug, "reference-sandbox")
        self.assertFalse(product.capabilities["near_me"])

    def test_09_registry_resolves_product_and_region(self):
        prachin = load_regional_product_v1(PRACHIN)
        second = load_regional_product_v1(SECOND)
        registry = RegionalProductRegistryV1((prachin, second))
        self.assertIs(registry.get_by_product_id("th-prachinburi"), prachin)
        self.assertIs(registry.resolve_region("reference-sandbox"), second)

    def test_10_unknown_region_fails_closed(self):
        registry = RegionalProductRegistryV1((load_regional_product_v1(PRACHIN),))
        with self.assertRaises(RegionalProductNotFoundError):
            registry.resolve_region("unknown-region")

    def test_11_duplicate_product_id_is_rejected(self):
        first = load_regional_product_v1(PRACHIN)
        payload = valid_payload()
        payload["region"]["slug"] = "other-slug"
        payload["region"]["code"] = "TH-XX"
        second = RegionalProductV1.from_mapping(payload)
        with self.assertRaises(RegionalProductContractError):
            RegionalProductRegistryV1((first, second))

    def test_12_duplicate_region_slug_is_rejected(self):
        first = load_regional_product_v1(PRACHIN)
        payload = valid_payload()
        payload["product_id"] = "th-other-product"
        payload["region"]["code"] = "TH-XX"
        second = RegionalProductV1.from_mapping(payload)
        with self.assertRaises(RegionalProductContractError):
            RegionalProductRegistryV1((first, second))

    def test_13_to_dict_returns_detached_mutable_copy(self):
        product = load_regional_product_v1(PRACHIN)
        exported = product.to_dict()
        exported["capabilities"]["places"] = False
        self.assertTrue(product.capabilities["places"])

    def test_14_bad_json_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text("{bad json", encoding="utf-8")
            with self.assertRaises(RegionalProductContractError):
                load_regional_product_v1(path)

    def test_15_input_mapping_is_not_retained_mutably(self):
        payload = valid_payload()
        product = RegionalProductV1.from_mapping(payload)
        payload["capabilities"]["places"] = False
        self.assertTrue(product.capabilities["places"])


if __name__ == "__main__":
    unittest.main()
