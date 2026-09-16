"""Compatibility wrapper for the Pathum decision reference model.

Canonical implementation:
    place_platform_v2.decision.scenarios.real_pathum_v1

The historical import path remains supported during Architecture Alignment V1.
"""
from __future__ import annotations

from .decision.scenarios import real_pathum_v1 as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

del _name
