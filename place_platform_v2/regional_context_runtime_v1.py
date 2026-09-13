from __future__ import annotations

import os
from pathlib import Path

from .regional_product_v1 import (
    RegionalProductContractError,
    RegionalProductNotFoundError,
    load_regional_product_registry_v1,
)
from .regional_reference_adapter_v1 import load_regional_reference_pack
from .regional_web_context_v1 import build_regional_web_context


def repository_root_v1() -> Path:
    """Resolve the read-only repository root for regional configuration.

    Docker currently copies the repository to /app, so the module-relative
    fallback remains stable there. The environment override exists for tests
    and alternate deploy layouts; it does not grant write authority.
    """

    configured = os.getenv("LOCALLIFE_REPOSITORY_ROOT", "").strip()
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[1]


def _product_paths(repository_root: Path) -> tuple[Path, ...]:
    regional_root = repository_root / "regional_products"
    if not regional_root.is_dir():
        raise RegionalProductContractError("regional_products_root_not_found")
    paths = tuple(sorted(regional_root.glob("*/product.json")))
    if not paths:
        raise RegionalProductContractError("regional_product_registry_empty")
    return paths


def regional_context_payload_v1(
    region_slug: str,
    *,
    repository_root: str | Path | None = None,
) -> dict[str, object]:
    """Build a public regional web context without embedding domain records."""

    if not isinstance(region_slug, str) or not region_slug.strip():
        raise RegionalProductNotFoundError("regional_product_not_found_for_region")
    root = Path(repository_root).resolve() if repository_root is not None else repository_root_v1()
    registry = load_regional_product_registry_v1(_product_paths(root))
    product = registry.resolve_region(region_slug.strip())
    pack = load_regional_reference_pack(product, root)
    return build_regional_web_context(pack).to_dict()
