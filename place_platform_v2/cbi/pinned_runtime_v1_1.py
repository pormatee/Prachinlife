from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .runtime_v1_1 import (
    DOMAIN_ID,
    DOMAIN_PACK_VERSION,
    RUNTIME_VERSION,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
)
from .runtime_v1_1.cbi.core_v1_1 import CBICoreV11
from .runtime_v1_1.domain_packs.locallife import DOMAIN_PACK


@dataclass(frozen=True)
class PinnedCBIRuntimeV11:
    core: Any
    domain_pack: Mapping[str, Any]

    source_repository: str = SOURCE_REPOSITORY
    source_commit: str = SOURCE_COMMIT
    runtime_version: str = RUNTIME_VERSION
    domain_id: str = DOMAIN_ID
    domain_pack_version: str = DOMAIN_PACK_VERSION


def build_pinned_cbi_v1_1(
    *,
    provider_port: Any = None,
) -> PinnedCBIRuntimeV11:
    core = CBICoreV11(
        provider_port=provider_port,
    )

    if str(core.runtime_version) != RUNTIME_VERSION:
        raise ValueError(
            "pinned_cbi_runtime_version_mismatch"
        )

    domain_pack = deepcopy(DOMAIN_PACK)

    if str(domain_pack.get("domain_id")) != DOMAIN_ID:
        raise ValueError(
            "pinned_cbi_domain_id_mismatch"
        )

    if (
        str(domain_pack.get("version"))
        != DOMAIN_PACK_VERSION
    ):
        raise ValueError(
            "pinned_cbi_domain_pack_version_mismatch"
        )

    return PinnedCBIRuntimeV11(
        core=core,
        domain_pack=domain_pack,
    )
