"""Transition Publication Boundary V1 for LocalLife/PrachinLife.

This module separates the audited legacy Published Projection baseline from
Canonical V2 publication. It has no DB access, writer imports, lifecycle
mutation, or evidence-creation authority.

Rules:
- legacy Published baseline is read-only during transition;
- legacy Published values may be presentation fallback only, never evidence;
- no write-back from legacy Published to Canonical;
- no new/updated data may be written into legacy bundles;
- lifecycle promotion must use the current verification/publication path;
- unknown operations fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping


BOUNDARY_VERSION = "TRANSITION-PUBLICATION-BOUNDARY-V1"
LEGACY_BASELINE_ID = "LEGACY-PUBLISHED-BASELINE-2026-09-12"
LEGACY_BASELINE_EXPECTED_COUNT = 923

_PRESENTATION_TAXONOMY = MappingProxyType(
    {
        "fuel": "ปั๊มน้ำมัน",
        "temple": "วัด / ศาสนสถาน",
        "restaurant": "ร้านอาหาร",
        "cafe": "คาเฟ่",
        "park": "สวน / พื้นที่พักผ่อน",
        "laundry": "ซักรีด",
        "car_repair": "ซ่อมรถ",
        "clinic": "คลินิก",
        "vegetarian": "vegetarian",
        "pharmacy": "ร้านยา",
        "nature": "ธรรมชาติ / จุดชมวิว",
        "attraction": "สถานที่ท่องเที่ยว",
    }
)


class BoundaryOperation(str, Enum):
    READ_LEGACY_BASELINE = "read_legacy_baseline"
    WRITE_LEGACY_BUNDLE = "write_legacy_bundle"
    WRITE_CANONICAL_FROM_LEGACY = "write_canonical_from_legacy"
    PROMOTE_LEGACY_LIFECYCLE = "promote_legacy_lifecycle"
    CREATE_EVIDENCE_FROM_LEGACY_PRESENTATION = "create_evidence_from_legacy_presentation"


class DisplayAddressSource(str, Enum):
    CANONICAL = "canonical"
    LEGACY_PUBLISHED_FALLBACK = "legacy_published_fallback"
    NONE = "none"


@dataclass(frozen=True)
class BoundaryDecision:
    allowed: bool
    reason: str
    boundary_version: str = BOUNDARY_VERSION


@dataclass(frozen=True)
class DisplayAddress:
    text: str | None
    source: DisplayAddressSource
    evidence_eligible: bool = False


class TransitionBoundaryViolation(RuntimeError):
    """Raised when a caller attempts an operation forbidden by this boundary."""


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).split()).strip()
    return cleaned or None


def presentation_taxonomy() -> Mapping[str, str]:
    """Return the immutable canonical-code -> display-label mapping."""
    return _PRESENTATION_TAXONOMY


def presentation_category_label(category_code: str) -> str:
    """Map a canonical code without guessing unknown taxonomy."""
    normalized = _clean_text(category_code)
    if normalized is None:
        raise ValueError("category_code is required")
    return _PRESENTATION_TAXONOMY.get(normalized.casefold(), normalized)


def presentation_categories(category_codes: Iterable[str]) -> tuple[str, ...]:
    """Map and de-duplicate labels while preserving input order."""
    out: list[str] = []
    seen: set[str] = set()
    for code in category_codes:
        label = presentation_category_label(code)
        key = label.casefold()
        if key not in seen:
            seen.add(key)
            out.append(label)
    return tuple(out)


def select_display_address(
    *,
    canonical_address: str | None,
    legacy_published_address: str | None,
) -> DisplayAddress:
    """Choose a UI address without mutating Canonical or creating evidence."""
    canonical = _clean_text(canonical_address)
    if canonical is not None:
        return DisplayAddress(canonical, DisplayAddressSource.CANONICAL)

    legacy = _clean_text(legacy_published_address)
    if legacy is not None:
        return DisplayAddress(legacy, DisplayAddressSource.LEGACY_PUBLISHED_FALLBACK)

    return DisplayAddress(None, DisplayAddressSource.NONE)


def authorize_boundary_operation(operation: BoundaryOperation | str) -> BoundaryDecision:
    """Authorize boundary operations. Unknown operations fail closed."""
    try:
        op = operation if isinstance(operation, BoundaryOperation) else BoundaryOperation(str(operation))
    except ValueError:
        return BoundaryDecision(False, "unknown operation: fail closed")

    if op is BoundaryOperation.READ_LEGACY_BASELINE:
        return BoundaryDecision(True, "legacy baseline is read-only during transition")

    reasons = {
        BoundaryOperation.WRITE_LEGACY_BUNDLE:
            "new or updated data must not be written to legacy bundle files",
        BoundaryOperation.WRITE_CANONICAL_FROM_LEGACY:
            "legacy Published fields are not canonical evidence and must not be written back",
        BoundaryOperation.PROMOTE_LEGACY_LIFECYCLE:
            "lifecycle promotion requires the current verification/publication path",
        BoundaryOperation.CREATE_EVIDENCE_FROM_LEGACY_PRESENTATION:
            "presentation fallback is non-evidentiary",
    }
    return BoundaryDecision(False, reasons[op])


def require_boundary_operation(operation: BoundaryOperation | str) -> None:
    decision = authorize_boundary_operation(operation)
    if not decision.allowed:
        raise TransitionBoundaryViolation(decision.reason)


def assert_legacy_baseline_count(actual_count: int) -> None:
    """Detect silent drift from the audited 923-row transition baseline."""
    if int(actual_count) != LEGACY_BASELINE_EXPECTED_COUNT:
        raise TransitionBoundaryViolation(
            f"legacy baseline count drift: expected {LEGACY_BASELINE_EXPECTED_COUNT}, got {actual_count}"
        )


NEW_DATA_REQUIRED_PATH = (
    "candidate_evidence",
    "verification_entity_resolution",
    "canonical",
    "publication_gate",
    "published_projection",
)

