from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "locallife.regional-product/v1"

_CAPABILITY_KEYS = frozenset(
    {
        "places",
        "near_me",
        "eat",
        "go",
        "services",
        "promotions",
        "regional_dna",
        "decision_api",
    }
)
_CONFIG_REF_KEYS = frozenset({"sources", "entity_keys", "taxonomy", "web"})
_ANALYTICS_KEYS = frozenset(
    {"regional_dna_semantics", "share_metric", "preserve_unresolved"}
)
_GOVERNANCE_KEYS = frozenset(
    {
        "fail_closed",
        "human_final_decision",
        "direct_canonical_write",
        "direct_published_write",
    }
)
_COMPATIBILITY_KEYS = frozenset(
    {"preserve_existing_prachinlife", "preserve_existing_api_outputs"}
)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_SAFE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_PRODUCT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class RegionalProductContractError(ValueError):
    """Raised when a regional-product declaration violates the V1 contract."""


class RegionalProductNotFoundError(LookupError):
    """Raised when a registry lookup cannot resolve a regional product."""


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RegionalProductContractError(f"{field}_must_be_object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], field: str) -> None:
    keys = set(value)
    missing = sorted(expected - keys)
    unknown = sorted(keys - expected)
    if missing:
        raise RegionalProductContractError(f"{field}_missing_keys:{','.join(missing)}")
    if unknown:
        raise RegionalProductContractError(f"{field}_unknown_keys:{','.join(unknown)}")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegionalProductContractError(f"{field}_must_be_nonempty_string")
    if value != value.strip():
        raise RegionalProductContractError(f"{field}_must_not_have_outer_whitespace")
    return value


def _boolean(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise RegionalProductContractError(f"{field}_must_be_boolean")
    return value


def _relative_config_ref(value: Any, field: str) -> str:
    ref = _text(value, field)
    if "\\" in ref:
        raise RegionalProductContractError(f"{field}_must_use_posix_separators")
    path = PurePosixPath(ref)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise RegionalProductContractError(f"{field}_must_be_safe_relative_path")
    if not path.parts or path.parts[0] != "regional_products":
        raise RegionalProductContractError(f"{field}_must_live_under_regional_products")
    return ref


def _freeze(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True, slots=True)
class RegionIdentityV1:
    country_code: str
    kind: str
    code: str
    slug: str
    name_th: str
    name_en: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RegionIdentityV1":
        payload = _object(payload, "region")
        _exact_keys(
            payload,
            frozenset({"country_code", "kind", "code", "slug", "name_th", "name_en"}),
            "region",
        )
        country_code = _text(payload["country_code"], "region.country_code")
        if not _COUNTRY_RE.fullmatch(country_code):
            raise RegionalProductContractError("region.country_code_invalid")
        kind = _text(payload["kind"], "region.kind")
        if not _SAFE_KEY_RE.fullmatch(kind):
            raise RegionalProductContractError("region.kind_invalid")
        slug = _text(payload["slug"], "region.slug")
        if not _SLUG_RE.fullmatch(slug):
            raise RegionalProductContractError("region.slug_invalid")
        return cls(
            country_code=country_code,
            kind=kind,
            code=_text(payload["code"], "region.code"),
            slug=slug,
            name_th=_text(payload["name_th"], "region.name_th"),
            name_en=_text(payload["name_en"], "region.name_en"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "country_code": self.country_code,
            "kind": self.kind,
            "code": self.code,
            "slug": self.slug,
            "name_th": self.name_th,
            "name_en": self.name_en,
        }


@dataclass(frozen=True, slots=True)
class RegionalProductV1:
    contract_version: str
    product_id: str
    brand: str
    region: RegionIdentityV1
    capabilities: Mapping[str, bool]
    config_refs: Mapping[str, str]
    analytics: Mapping[str, Any]
    governance: Mapping[str, bool]
    compatibility: Mapping[str, bool]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RegionalProductV1":
        payload = _object(payload, "regional_product")
        _exact_keys(
            payload,
            frozenset(
                {
                    "contract_version",
                    "product_id",
                    "brand",
                    "region",
                    "capabilities",
                    "config_refs",
                    "analytics",
                    "governance",
                    "compatibility",
                }
            ),
            "regional_product",
        )

        version = _text(payload["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise RegionalProductContractError("unsupported_contract_version")

        product_id = _text(payload["product_id"], "product_id")
        if not _PRODUCT_ID_RE.fullmatch(product_id):
            raise RegionalProductContractError("product_id_invalid")

        capabilities_raw = _object(payload["capabilities"], "capabilities")
        _exact_keys(capabilities_raw, _CAPABILITY_KEYS, "capabilities")
        capabilities = {
            key: _boolean(capabilities_raw[key], f"capabilities.{key}")
            for key in sorted(_CAPABILITY_KEYS)
        }

        config_refs_raw = _object(payload["config_refs"], "config_refs")
        _exact_keys(config_refs_raw, _CONFIG_REF_KEYS, "config_refs")
        config_refs = {
            key: _relative_config_ref(config_refs_raw[key], f"config_refs.{key}")
            for key in sorted(_CONFIG_REF_KEYS)
        }

        analytics_raw = _object(payload["analytics"], "analytics")
        _exact_keys(analytics_raw, _ANALYTICS_KEYS, "analytics")
        analytics = {
            "regional_dna_semantics": _text(
                analytics_raw["regional_dna_semantics"], "analytics.regional_dna_semantics"
            ),
            "share_metric": _text(analytics_raw["share_metric"], "analytics.share_metric"),
            "preserve_unresolved": _boolean(
                analytics_raw["preserve_unresolved"], "analytics.preserve_unresolved"
            ),
        }

        governance_raw = _object(payload["governance"], "governance")
        _exact_keys(governance_raw, _GOVERNANCE_KEYS, "governance")
        governance = {
            key: _boolean(governance_raw[key], f"governance.{key}")
            for key in sorted(_GOVERNANCE_KEYS)
        }
        if governance["fail_closed"] is not True:
            raise RegionalProductContractError("governance.fail_closed_must_be_true")
        if governance["human_final_decision"] is not True:
            raise RegionalProductContractError(
                "governance.human_final_decision_must_be_true"
            )
        if governance["direct_canonical_write"] is not False:
            raise RegionalProductContractError(
                "governance.direct_canonical_write_must_be_false"
            )
        if governance["direct_published_write"] is not False:
            raise RegionalProductContractError(
                "governance.direct_published_write_must_be_false"
            )

        compatibility_raw = _object(payload["compatibility"], "compatibility")
        _exact_keys(compatibility_raw, _COMPATIBILITY_KEYS, "compatibility")
        compatibility = {
            key: _boolean(compatibility_raw[key], f"compatibility.{key}")
            for key in sorted(_COMPATIBILITY_KEYS)
        }

        return cls(
            contract_version=version,
            product_id=product_id,
            brand=_text(payload["brand"], "brand"),
            region=RegionIdentityV1.from_mapping(payload["region"]),
            capabilities=_freeze(capabilities),
            config_refs=_freeze(config_refs),
            analytics=_freeze(analytics),
            governance=_freeze(governance),
            compatibility=_freeze(compatibility),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "product_id": self.product_id,
            "brand": self.brand,
            "region": self.region.to_dict(),
            "capabilities": dict(self.capabilities),
            "config_refs": dict(self.config_refs),
            "analytics": dict(self.analytics),
            "governance": dict(self.governance),
            "compatibility": dict(self.compatibility),
        }


class RegionalProductRegistryV1:
    """Read-only regional-product registry with fail-closed lookups."""

    def __init__(self, products: Iterable[RegionalProductV1]):
        by_product_id: dict[str, RegionalProductV1] = {}
        by_region_slug: dict[str, RegionalProductV1] = {}
        for product in products:
            if not isinstance(product, RegionalProductV1):
                raise RegionalProductContractError("registry_product_type_invalid")
            if product.product_id in by_product_id:
                raise RegionalProductContractError(
                    f"duplicate_product_id:{product.product_id}"
                )
            if product.region.slug in by_region_slug:
                raise RegionalProductContractError(
                    f"duplicate_region_slug:{product.region.slug}"
                )
            by_product_id[product.product_id] = product
            by_region_slug[product.region.slug] = product
        self._by_product_id = MappingProxyType(by_product_id)
        self._by_region_slug = MappingProxyType(by_region_slug)

    def get_by_product_id(self, product_id: str) -> RegionalProductV1:
        try:
            return self._by_product_id[product_id]
        except KeyError as exc:
            raise RegionalProductNotFoundError(
                f"regional_product_not_found:{product_id}"
            ) from exc

    def resolve_region(self, region_slug: str) -> RegionalProductV1:
        try:
            return self._by_region_slug[region_slug]
        except KeyError as exc:
            raise RegionalProductNotFoundError(
                f"regional_product_not_found_for_region:{region_slug}"
            ) from exc

    def list_products(self) -> tuple[RegionalProductV1, ...]:
        return tuple(self._by_product_id[key] for key in sorted(self._by_product_id))


def load_regional_product_v1(path: str | Path) -> RegionalProductV1:
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegionalProductContractError(
            f"regional_product_load_failed:{path}"
        ) from exc
    return RegionalProductV1.from_mapping(payload)


def load_regional_product_registry_v1(
    paths: Iterable[str | Path],
) -> RegionalProductRegistryV1:
    return RegionalProductRegistryV1(load_regional_product_v1(path) for path in paths)
