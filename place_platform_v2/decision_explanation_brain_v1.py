"""Compatibility wrapper for LocalLife Decision Explanation Brain V1.

Canonical implementation:
    place_platform_v2.decision.explanation_brain_v1
"""
from __future__ import annotations
from .decision import explanation_brain_v1 as _impl
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
del _name
