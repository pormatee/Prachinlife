from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.regional_product_v1 import RegionalProductV1
from place_platform_v2.regional_reference_adapter_v1 import (
    RegionalReferencePackError,
    load_regional_reference_pack,
)
from place_platform_v2.regional_web_context_v1 import build_regional_web_context

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_PATH = ROOT / "regional_products" / "prachinburi" / "product.json"


def load_product(path=PRODUCT_PATH):
    return RegionalProductV1.from_mapping(json.loads(Path(path).read_text(encoding="utf-8")))


class TestRegionalReferenceAdapterV1(unittest.TestCase):
    def test_01_prachin_reference_pack_loads(self):
        pack = load_regional_reference_pack(load_product(), ROOT)
        self.assertEqual(pack.product.region.slug, "prachinburi")
        self.assertEqual(set(pack.configs), {"sources", "entity_keys", "taxonomy", "web"})

    def test_02_w1_source_scope_is_read_only_and_not_evidence(self):
        pack = load_regional_reference_pack(load_product(), ROOT)
        cfg = pack.config("sources")
        self.assertEqual(cfg["region_scope"]["iso3166_2"], "TH-25")
        source = cfg["discovery_sources"][0]
        self.assertEqual(source["mode"], "read_only_candidate_discovery")
        self.assertIs(source["province_scope_is_explicit_source_claim"], False)
        self.assertIs(cfg["governance"]["direct_canonical_write"], False)
        self.assertIs(cfg["governance"]["direct_published_write"], False)

    def test_03_required_path_preserves_existing_pipeline(self):
        pack = load_regional_reference_pack(load_product(), ROOT)
        self.assertEqual(pack.config("sources")["required_path"], [
            "source_candidate", "intake_triage", "entity_resolution_dedup",
            "field_evidence", "verification", "adoption", "canonical",
            "publication_gate", "published_projection",
        ])

    def test_04_taxonomy_is_one_way_only(self):
        cfg = load_regional_reference_pack(load_product(), ROOT).config("taxonomy")
        self.assertEqual(cfg["direction"], "canonical_to_presentation_only")
        self.assertIs(cfg["reverse_mapping_allowed"], False)
        self.assertEqual(cfg["mapping"]["restaurant"], "ร้านอาหาร")

    def test_05_entity_keys_do_not_invent_regional_overrides(self):
        cfg = load_regional_reference_pack(load_product(), ROOT).config("entity_keys")
        self.assertEqual(cfg["authority_mode"], "existing_core")
        self.assertEqual(cfg["regional_overrides"], {})
        self.assertIs(cfg["governance"]["direct_write"], False)

    def test_06_web_context_contains_no_place_records(self):
        pack = load_regional_reference_pack(load_product(), ROOT)
        context = build_regional_web_context(pack).to_dict()
        self.assertEqual(context["contract_version"], "locallife.regional-web-context/v1")
        self.assertEqual(context["region_slug"], "prachinburi")
        self.assertEqual(context["endpoints"]["decision"], "/v1/decision")
        self.assertIs(context["freshness"]["place_data_embedded"], False)
        self.assertNotIn("places", context)

    def test_07_missing_config_fails_closed(self):
        product = load_product()
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RegionalReferencePackError, "config_not_found"):
                load_regional_reference_pack(product, td)

    def test_08_config_product_mismatch_fails_closed(self):
        product = load_product()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            for label, ref in product.config_refs.items():
                target = temp / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                payload = json.loads((ROOT / ref).read_text(encoding="utf-8"))
                if label == "sources": payload["product_id"] = "wrong-product"
                target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(RegionalReferencePackError, "config_product_mismatch:sources"):
                load_regional_reference_pack(product, temp)

    def test_09_reverse_taxonomy_is_rejected(self):
        product = load_product()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            for label, ref in product.config_refs.items():
                target = temp / ref; target.parent.mkdir(parents=True, exist_ok=True)
                payload = json.loads((ROOT / ref).read_text(encoding="utf-8"))
                if label == "taxonomy": payload["reverse_mapping_allowed"] = True
                target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(RegionalReferencePackError, "taxonomy_reverse_mapping_forbidden"):
                load_regional_reference_pack(product, temp)

    def test_10_web_direct_domain_data_is_rejected(self):
        product = load_product()
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            for label, ref in product.config_refs.items():
                target=temp/ref; target.parent.mkdir(parents=True,exist_ok=True)
                payload=json.loads((ROOT/ref).read_text(encoding="utf-8"))
                if label=="web": payload["direct_domain_data"] = True
                target.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(RegionalReferencePackError, "web_direct_domain_data_forbidden"):
                load_regional_reference_pack(product,temp)

    def test_11_adapter_is_region_agnostic_with_synthetic_second_region(self):
        p = load_product().to_dict()
        p["product_id"]="th-reference-sandbox"; p["brand"]="ReferenceLife"
        p["region"].update({"code":"TH-ZZ","slug":"reference-sandbox","name_th":"จังหวัดทดสอบ","name_en":"Reference Sandbox"})
        base="regional_products/reference-sandbox"
        p["config_refs"]={k:f"{base}/{k}.json" for k in ("sources","entity_keys","taxonomy","web")}
        product=RegionalProductV1.from_mapping(p)
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td); (temp/base).mkdir(parents=True)
            for label in ("sources","entity_keys","taxonomy","web"):
                source=json.loads((ROOT/f"regional_products/prachinburi/{label}.json").read_text(encoding="utf-8"))
                source["product_id"]=product.product_id
                if label=="sources": source["region_scope"].update({"region_code":"TH-ZZ","region_slug":"reference-sandbox","province_name":"จังหวัดทดสอบ","iso3166_2":"TH-ZZ"})
                if label=="web":
                    source["brand"]["name"]="ReferenceLife"
                    source["routes"]={k:v.replace("prachinburi","reference-sandbox") for k,v in source["routes"].items()}
                    source["regional_context_endpoint"]="/v1/regions/reference-sandbox/context"
                (temp/f"{base}/{label}.json").write_text(json.dumps(source,ensure_ascii=False),encoding="utf-8")
            pack=load_regional_reference_pack(product,temp)
            context=build_regional_web_context(pack)
            self.assertEqual(context.region_slug,"reference-sandbox")
            self.assertEqual(context.brand,"ReferenceLife")
