"""Compatibility wrapper for LocalLife Phase 7 Decision Assistant.

Canonical implementation:
    place_platform_v2.decision.phase7_assistant
"""
from __future__ import annotations

from .decision import phase7_assistant as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

del _name
