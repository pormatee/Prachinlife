"""Compatibility wrapper for the LocalLife regional reference adapter.

Canonical implementation:
    place_platform_v2.regional.reference_adapter_v1

This wrapper remains during Architecture Alignment V1 so existing imports keep
working while callers migrate incrementally.
"""
from __future__ import annotations

from .regional import reference_adapter_v1 as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

del _name
