"""LocalLife boundary for shared MEasyMate CBI runtime.

Wave 6A is shadow-only.
CBI Core remains owned by MEasyMate CBI.
"""

from .adapter_v1 import (
    CBI_DOMAIN_ID,
    CBI_DOMAIN_PACK_VERSION,
    CBI_MODE,
    CBI_RUNTIME_COMMIT,
    CBI_RUNTIME_VERSION,
    CBIShadowObservationV1,
    LocalLifeCBIShadowAdapterV1,
)

__all__ = [
    "CBI_DOMAIN_ID",
    "CBI_DOMAIN_PACK_VERSION",
    "CBI_MODE",
    "CBI_RUNTIME_COMMIT",
    "CBI_RUNTIME_VERSION",
    "CBIShadowObservationV1",
    "LocalLifeCBIShadowAdapterV1",
]
