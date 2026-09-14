from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .reference_adapter_v1 import RegionalReferencePackV1, RegionalReferencePackError

CONTRACT_VERSION = "locallife.regional-web-context/v1"

@dataclass(frozen=True, slots=True)
class RegionalWebContextV1:
    contract_version: str
    product_id: str
    region_slug: str
    brand: str
    locale: str
    capabilities: Mapping[str, bool]
    navigation: tuple[Mapping[str, str], ...]
    endpoints: Mapping[str, str]
    routes: Mapping[str, str]
    freshness: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "product_id": self.product_id,
            "region_slug": self.region_slug,
            "brand": self.brand,
            "locale": self.locale,
            "capabilities": dict(self.capabilities),
            "navigation": [dict(item) for item in self.navigation],
            "endpoints": dict(self.endpoints),
            "routes": dict(self.routes),
            "freshness": dict(self.freshness),
        }


def build_regional_web_context(pack: RegionalReferencePackV1) -> RegionalWebContextV1:
    if not isinstance(pack, RegionalReferencePackV1):
        raise RegionalReferencePackError("reference_pack_type_invalid")
    web = pack.config("web")
    locale = web.get("locale")
    if not isinstance(locale, str) or not locale.strip():
        raise RegionalReferencePackError("web_locale_required")
    nav = web.get("navigation")
    if not isinstance(nav, list):
        raise RegionalReferencePackError("web_navigation_must_be_array")
    clean_nav = []
    for item in nav:
        if not isinstance(item, dict) or set(item) != {"id", "label"}:
            raise RegionalReferencePackError("web_navigation_item_invalid")
        if not all(isinstance(item[k], str) and item[k].strip() for k in ("id", "label")):
            raise RegionalReferencePackError("web_navigation_item_invalid")
        clean_nav.append(MappingProxyType(dict(item)))
    routes = web.get("routes")
    if not isinstance(routes, dict) or not routes:
        raise RegionalReferencePackError("web_routes_required")
    if any(not isinstance(k, str) or not isinstance(v, str) or not v.startswith("/") for k,v in routes.items()):
        raise RegionalReferencePackError("web_route_invalid")
    decision = web.get("decision_endpoint")
    regional = web.get("regional_context_endpoint")
    if not isinstance(decision, str) or not decision.startswith("/"):
        raise RegionalReferencePackError("decision_endpoint_invalid")
    if not isinstance(regional, str) or not regional.startswith("/"):
        raise RegionalReferencePackError("regional_context_endpoint_invalid")
    brand_payload = web.get("brand")
    if not isinstance(brand_payload, dict) or brand_payload.get("name") != pack.product.brand:
        raise RegionalReferencePackError("web_brand_mismatch")
    return RegionalWebContextV1(
        contract_version=CONTRACT_VERSION,
        product_id=pack.product.product_id,
        region_slug=pack.product.region.slug,
        brand=pack.product.brand,
        locale=locale,
        capabilities=MappingProxyType(dict(pack.product.capabilities)),
        navigation=tuple(clean_nav),
        endpoints=MappingProxyType({"decision": decision, "regional_context": regional}),
        routes=MappingProxyType(dict(routes)),
        freshness=MappingProxyType({"mode":"read_model_owned","place_data_embedded":False}),
    )
