"""Compatibility alias for LocalLife Prachinburi expansion intake V1.

Canonical implementation:
    place_platform_v2.intake.prachinburi_expansion_v1
"""

from __future__ import annotations

import sys as _sys
from .intake import prachinburi_expansion_v1 as _impl

_sys.modules[__name__] = _impl
