from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import EvidenceStatus, GeoPoint, SourceRef
from .models import EvidenceKind, PlaceEvidence, PlaceLifecycle
from .publication_export import _load_places_and_evidence
from .publication_readiness import evidence_lineage_key

POLICY_VERSION = "2W.4-verification-source-acquisition-v1"
STRONG_GEO_MATCH_METERS = 150.0
SCOPE_CONFLICT_METERS = 500.0


@dataclass(frozen=True)
class SourceObservation:
    source: SourceRef
    place_name: str
    province: str | None
    location: GeoPoint | None
    lifecycle: PlaceLifecycle | None = None
    address_text: str | None = None
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceAcquisitionResult:
    mode: str
    result: str
    reason: str
    place_id: str
    canonical_name: str
    canonical_province: str | None
    source_name: str
    source_place_name: str
    source_province: str | None
    distance_m: float | None
    name_compatible: bool
    province_compatible: bool | None
    source_lineage: str
    independent_lineage: bool
    can_create_verification_bundle: bool
    required_action: str
    publication_performed: bool = False
    user_web_switched: bool = False
    policy_version: str = POLICY_VERSION


def _text(value: str | None) -> str:
    return (value or "").strip().casefold()


def _name_key(value: str | None) -> str:
    text = _text(value)
    text = re.sub(r"[\s\-_/.,()]+", "", text)
    aliases = {
        "caltex": "caltex",
        "คาลเท็กซ์": "caltex",
        "ปั๊มคาลเท็กซ์": "caltex",
        "สถานีบริการคาลเท็กซ์": "caltex",
    }
    if text in aliases:
        return aliases[text]
    # Brand-preserving match for branch labels such as "คาลเท็กซ์ สาขา...".
    if "คาลเท็กซ์" in text or "caltex" in text:
        return "caltex"
    return text


def _province_key(value: str | None) -> str:
    text = _text(value)
    text = text.replace("จังหวัด", "").replace("จ.", "")
    return re.sub(r"\s+", "", text)


def _distance_m(a: GeoPoint | None, b: GeoPoint | None) -> float | None:
    if a is None or b is None:
        return None
    r = 6371008.8
    p1 = math.radians(a.latitude)
    p2 = math.radians(b.latitude)
    dp = math.radians(b.latitude - a.latitude)
    dl = math.radians(b.longitude - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * (2 * math.atan2(math.sqrt(h), math.sqrt(1 - h)))


def _source_lineage(place_id: str, source: SourceRef) -> str:
    probe = PlaceEvidence(
        place_id=place_id,
        source=source,
        kind=EvidenceKind.OTHER,
        field_name="acquisition_probe",
        value=True,
        status=EvidenceStatus.CANDIDATE,
        observed_at=source.observed_at,
    )
    return evidence_lineage_key(probe)


def _existing_lineages(evidence) -> set[str]:
    return {
        evidence_lineage_key(item)
        for item in evidence
        if item.status not in {EvidenceStatus.REJECTED, EvidenceStatus.STALE}
    }


def evaluate_source_observation(
    database_path: str | Path,
    *,
    place_id: str,
    observation: SourceObservation,
) -> SourceAcquisitionResult:
    # Read canonical province first so this works for any province-scoped dataset.
    import sqlite3

    db = Path(database_path).resolve()
    con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT province FROM places WHERE place_id=?",
            (place_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise KeyError(f"unknown place_id: {place_id}")

    canonical_province = row[0]
    places, by_place = _load_places_and_evidence(database_path, canonical_province)
    place = next((item for item in places if item.identity.place_id == place_id), None)
    if place is None:
        raise KeyError(f"unknown place_id: {place_id}")

    evidence = by_place.get(place_id, ())
    lineage = _source_lineage(place_id, observation.source)
    independent = lineage not in _existing_lineages(evidence)
    distance = _distance_m(place.location, observation.location)
    name_ok = _name_key(place.canonical_name) == _name_key(observation.place_name)
    province_ok = (
        None
        if observation.province is None or place.province is None
        else _province_key(place.province) == _province_key(observation.province)
    )

    common = dict(
        mode="READ_ONLY",
        place_id=place_id,
        canonical_name=place.canonical_name,
        canonical_province=place.province,
        source_name=observation.source.source_name,
        source_place_name=observation.place_name,
        source_province=observation.province,
        distance_m=(round(distance, 1) if distance is not None else None),
        name_compatible=name_ok,
        province_compatible=province_ok,
        source_lineage=lineage,
        independent_lineage=independent,
    )

    # A strong geographic anchor that contradicts province is a critical scope conflict.
    if distance is not None and distance <= SCOPE_CONFLICT_METERS and province_ok is False:
        return SourceAcquisitionResult(
            result="scope_conflict",
            reason=(
                "source observation is geographically anchored to this canonical place "
                "but reports a different province"
            ),
            can_create_verification_bundle=False,
            required_action="canonical_correction_review",
            **common,
        )

    if not name_ok and distance is not None and distance <= STRONG_GEO_MATCH_METERS:
        return SourceAcquisitionResult(
            result="identity_conflict",
            reason="source is very near the canonical location but place identity/name conflicts",
            can_create_verification_bundle=False,
            required_action="entity_resolution_review",
            **common,
        )

    if observation.location is None:
        return SourceAcquisitionResult(
            result="insufficient_anchor",
            reason="source observation has no location anchor; cannot bind it to this canonical place safely",
            can_create_verification_bundle=False,
            required_action="acquire_location_or_address_anchor",
            **common,
        )

    if distance is None or distance > STRONG_GEO_MATCH_METERS:
        return SourceAcquisitionResult(
            result="unresolved_match",
            reason="source observation is not geographically close enough for deterministic verification binding",
            can_create_verification_bundle=False,
            required_action="manual_source_matching_review",
            **common,
        )

    if province_ok is not True:
        return SourceAcquisitionResult(
            result="insufficient_scope",
            reason="source observation does not positively confirm the canonical province",
            can_create_verification_bundle=False,
            required_action="acquire_explicit_province_evidence",
            **common,
        )

    if not name_ok:
        return SourceAcquisitionResult(
            result="identity_conflict",
            reason="source place name does not agree with canonical identity",
            can_create_verification_bundle=False,
            required_action="entity_resolution_review",
            **common,
        )

    if not independent:
        return SourceAcquisitionResult(
            result="blocked_same_lineage",
            reason="source observation is not independent from existing evidence lineage",
            can_create_verification_bundle=False,
            required_action="acquire_independent_source",
            **common,
        )

    if observation.lifecycle is not PlaceLifecycle.ACTIVE:
        return SourceAcquisitionResult(
            result="identity_match_no_lifecycle",
            reason="source binds to the canonical identity but does not explicitly verify lifecycle=active",
            can_create_verification_bundle=False,
            required_action="acquire_explicit_active_lifecycle_evidence",
            **common,
        )

    return SourceAcquisitionResult(
        result="verification_candidate",
        reason=(
            "independent source agrees on identity, province, location, and active lifecycle; "
            "eligible to be converted into a Phase 2W.3 verification bundle"
        ),
        can_create_verification_bundle=True,
        required_action="phase2w3_dry_run",
        **common,
    )
