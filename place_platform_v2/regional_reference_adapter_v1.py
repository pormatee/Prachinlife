from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .regional_product_v1 import RegionalProductContractError, RegionalProductV1

_REFERENCE_CONTRACTS = {
    "sources": "locallife.regional-sources/v1",
    "entity_keys": "locallife.regional-entity-keys/v1",
    "taxonomy": "locallife.regional-taxonomy-presentation/v1",
    "web": "locallife.regional-web/v1",
}

class RegionalReferencePackError(RegionalProductContractError):
    """Raised when referenced regional configuration is missing or unsafe."""


def _frozen(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegionalReferencePackError(f"config_not_found:{label}") from exc
    except json.JSONDecodeError as exc:
        raise RegionalReferencePackError(f"config_invalid_json:{label}") from exc
    if not isinstance(value, dict):
        raise RegionalReferencePackError(f"config_must_be_object:{label}")
    return value


def _resolve_ref(repository_root: Path, ref: str) -> Path:
    root = repository_root.resolve()
    path = (root / ref).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RegionalReferencePackError("config_ref_escapes_repository") from exc
    return path


def _validate_common(product: RegionalProductV1, label: str, payload: Mapping[str, Any]) -> None:
    expected = _REFERENCE_CONTRACTS[label]
    if payload.get("contract_version") != expected:
        raise RegionalReferencePackError(f"unsupported_config_contract:{label}")
    if payload.get("product_id") != product.product_id:
        raise RegionalReferencePackError(f"config_product_mismatch:{label}")


def _validate_governance(product: RegionalProductV1, configs: Mapping[str, Mapping[str, Any]]) -> None:
    if product.governance["direct_canonical_write"] or product.governance["direct_published_write"]:
        raise RegionalReferencePackError("product_write_authority_forbidden")

    sources = configs["sources"]
    source_governance = sources.get("governance")
    if not isinstance(source_governance, dict):
        raise RegionalReferencePackError("sources_governance_required")
    if source_governance.get("fail_closed") is not True:
        raise RegionalReferencePackError("sources_fail_closed_required")
    if source_governance.get("direct_canonical_write") is not False:
        raise RegionalReferencePackError("sources_direct_canonical_write_forbidden")
    if source_governance.get("direct_published_write") is not False:
        raise RegionalReferencePackError("sources_direct_published_write_forbidden")
    if source_governance.get("legacy_presentation_as_evidence") is not False:
        raise RegionalReferencePackError("legacy_presentation_evidence_forbidden")

    taxonomy = configs["taxonomy"]
    if taxonomy.get("direction") != "canonical_to_presentation_only":
        raise RegionalReferencePackError("taxonomy_direction_must_be_one_way")
    if taxonomy.get("reverse_mapping_allowed") is not False:
        raise RegionalReferencePackError("taxonomy_reverse_mapping_forbidden")

    entity_keys = configs["entity_keys"]
    ek_governance = entity_keys.get("governance")
    if not isinstance(ek_governance, dict) or ek_governance.get("direct_write") is not False:
        raise RegionalReferencePackError("entity_keys_direct_write_forbidden")

    web = configs["web"]
    if web.get("direct_domain_data") is not False:
        raise RegionalReferencePackError("web_direct_domain_data_forbidden")


@dataclass(frozen=True, slots=True)
class RegionalReferencePackV1:
    """Read-only regional configuration exposed behind a product boundary.

    The adapter intentionally treats configuration as data and imports no named
    regional business-policy module. Domain algorithms remain in the existing core.
    """

    product: RegionalProductV1
    configs: Mapping[str, Mapping[str, Any]]

    def config(self, label: str) -> Mapping[str, Any]:
        try:
            return self.configs[label]
        except KeyError as exc:
            raise RegionalReferencePackError(f"unknown_config_label:{label}") from exc


def load_regional_reference_pack(product: RegionalProductV1, repository_root: str | Path) -> RegionalReferencePackV1:
    if not isinstance(product, RegionalProductV1):
        raise RegionalReferencePackError("product_type_invalid")
    root = Path(repository_root)
    loaded: dict[str, Mapping[str, Any]] = {}
    for label, ref in product.config_refs.items():
        payload = _load_json_object(_resolve_ref(root, ref), label)
        _validate_common(product, label, payload)
        loaded[label] = _frozen(payload)
    _validate_governance(product, loaded)
    return RegionalReferencePackV1(product=product, configs=MappingProxyType(loaded))
