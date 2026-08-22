from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import PlaceLifecycle
from .publication import PublicationPolicy
from .publication_export import _load_places_and_evidence
from .verification import VerificationPolicy, verify_field

PHASE2W2_POLICY_VERSION = '2W.2-publication-readiness-v1'
_REQUIRED = ('canonical_name','categories','lifecycle','location','province')


def _osm_identity(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r'(?:osm[-:/ ]*)?(?:node|way|relation)[-:/ ]*(\d+)', text, re.I)
    if m:
        kind = re.search(r'(node|way|relation)', text, re.I)
        return f"osm:{(kind.group(1).lower() if kind else 'object')}:{m.group(1)}"
    m = re.search(r'openstreetmap\.org/(node|way|relation)/(\d+)', text, re.I)
    if m:
        return f'osm:{m.group(1).lower()}:{m.group(2)}'
    return None


def evidence_lineage_key(evidence) -> str:
    md = dict(evidence.metadata or {})
    candidates = (
        md.get('underlying_seed_source_url'), md.get('underlying_seed_source_name'),
        evidence.source.source_url, evidence.source.source_record_id,
    )
    for value in candidates:
        key = _osm_identity(str(value) if value is not None else None)
        if key:
            return key
    return '|'.join((
        evidence.source.source_type.value,
        evidence.source.source_name.strip().casefold(),
        (evidence.source.source_record_id or '').strip().casefold(),
    ))


def lineage_source_count(evidence, field_name: str, value) -> int:
    keys = set()
    for item in evidence:
        if item.field_name != field_name or item.value != value:
            continue
        if item.status.value in {'rejected','stale'}:
            continue
        keys.add(evidence_lineage_key(item))
    return len(keys)


@dataclass(frozen=True)
class PilotReadiness:
    place_id: str
    canonical_name: str
    lifecycle: str
    legacy_verified_fields: tuple[str, ...]
    lineage_verified_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    reasons: tuple[str, ...]
    publication_ready: bool
    policy_version: str = PHASE2W2_POLICY_VERSION


def evaluate_pilot_readiness(database_path: str | Path, place_id: str) -> PilotReadiness:
    places, by_place = _load_places_and_evidence(database_path, 'ปราจีนบุรี')
    place = next((p for p in places if p.identity.place_id == place_id), None)
    if place is None:
        raise KeyError(f'unknown Prachinburi place_id: {place_id}')
    evidence = by_place.get(place_id, ())
    vpolicy = VerificationPolicy()
    legacy_verified=[]; lineage_verified=[]; blocked=[]; reasons=[]
    for field in _REQUIRED:
        verification=verify_field(place_id=place_id, field_name=field, evidence=evidence, policy=vpolicy)
        if verification.outcome.value == 'verified' and verification.selected_value == getattr(place,field):
            legacy_verified.append(field)
        value=getattr(place,field)
        count=lineage_source_count(evidence, field, value)
        if count >= vpolicy.verified_independent_sources:
            lineage_verified.append(field)
        else:
            blocked.append(field)
            reasons.append(f'{field} has {count} independent lineage source(s); requires {vpolicy.verified_independent_sources}')
    if place.lifecycle is not PlaceLifecycle.ACTIVE:
        reasons.append('canonical lifecycle is not active')
    ready=(place.lifecycle is PlaceLifecycle.ACTIVE and not blocked)
    return PilotReadiness(place_id,place.canonical_name,place.lifecycle.value,tuple(legacy_verified),tuple(lineage_verified),tuple(blocked),tuple(reasons),ready)
