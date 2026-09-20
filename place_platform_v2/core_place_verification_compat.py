"""Compatibility wrapper for LocalLife Core Place Verification.

Canonical implementation:
    place_platform_v2.compat.core_place_verification_v1
"""

from __future__ import annotations

from pathlib import Path

from .compat import core_place_verification_v1 as _impl


# Preserve the historical physical-path contract.
def _compat_project_root():
    root = Path(__file__).resolve().parents[1]
    return root


COORDINATE_REPORT_NAMES = _impl.COORDINATE_REPORT_NAMES
evaluate_compatibility = _impl.evaluate_compatibility
_load_coordinate_results = _impl._load_coordinate_results


def __getattr__(name):
    return getattr(_impl, name)
