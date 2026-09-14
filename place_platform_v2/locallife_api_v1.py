"""Compatibility entrypoint for LocalLife API V1.

Canonical implementation:
    place_platform_v2.api.locallife_v1

Imported use aliases the historical module name directly to the canonical
module object so monkeypatching and symbol binding remain compatible.

Historical launch command preserved:
    python -m place_platform_v2.locallife_api_v1
"""
from __future__ import annotations

import sys as _sys
from .api import locallife_v1 as _impl

if __name__ == "__main__":
    _impl.serve()
else:
    _sys.modules[__name__] = _impl
