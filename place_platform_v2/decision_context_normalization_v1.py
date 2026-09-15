"""Compatibility wrapper for LocalLife decision context normalization V1.

Canonical implementation:
    place_platform_v2.decision.context_normalization_v1

The historical import path remains supported during architecture alignment.
"""
from __future__ import annotations

from .decision.context_normalization_v1 import (
    _first_number,
    normalize_decision_context_v1,
)

__all__ = ["normalize_decision_context_v1"]
