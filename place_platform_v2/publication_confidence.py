from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import PlaceLifecycle
from .publication_export import _load_places_and_evidence
from .publication_readiness import evidence_lineage_key

POLICY_VERSION = '2W.8-publication-confidence-v1'
CORE_FIELDS = ('canonical_name','location','province','categories')
OPTIONAL_FIELDS = ('address_text','phone','website')

TRUSTED_CLASSES = frozenset({'direct_osm','admin_operator','independent_source'})


def _trust_class(e) -> str:
    md=dict(e.metadata or {})
    name=e.source.source_name.strip().casefold()
    url=(e.source.source_url or '').casefold()
    rec=(e.source.source_record_id or '').casefold()
    if md.get('provenance_origin') == 'operator_change' or name == 'prachinlife admin operator':
        return 'admin_operator'
    if 'openstreetmap' in name or 'openstreetmap.org' in url:
        return 'direct_osm'
    if name == 'prachinlife-v1-json':
        return 'v1_derived_osm' if ('osm-' in rec or 'openstreetmap' in str(md).casefold()) else 'legacy_v1'
    if e.source.source_url or e.source.source_record_id:
        return 'independent_source'
    return 'legacy_unknown'


def _matching(evidence: Iterable, field: str, value):
    return tuple(e for e in evidence if e.field_name == field and e.value == value and e.status.value not in {'rejected','stale'})


def _lineages(items):
    return {evidence_lineage_key(e) for e in items}


def _trusted_lineages(items):
    return {evidence_lineage_key(e) for e in items if _trust_class(e) in TRUSTED_CLASSES}


def _has_conflict(evidence, field, value) -> bool:
    vals=[]
    for e in evidence:
        if e.field_name != field or e.status.value in {'rejected','stale'}:
            continue
        if e.value != value:
            vals.append(e)
    return bool(vals)

@dataclass(frozen=True)
class ConfidenceDecision:
    place_id: str
    name: str
    outcome: str
    reasons: tuple[str,...]
    core_supported: tuple[str,...]
    optional_publishable: tuple[str,...]
    lifecycle_evidence_lineages: int
    policy_version: str = POLICY_VERSION


def evaluate_place(place, evidence) -> ConfidenceDecision:
    reasons=[]; supported=[]; optional=[]
    for field in CORE_FIELDS:
        value=getattr(place,field)
        if value is None or value == () or (isinstance(value,str) and not value.strip()):
            reasons.append(f'{field} missing canonical value'); continue
        items=_matching(evidence,field,value)
        if not _lineages(items):
            reasons.append(f'{field} has no supporting lineage'); continue
        if _has_conflict(evidence,field,value):
            reasons.append(f'{field} has conflicting evidence'); continue
        supported.append(field)
    # Existence/lifecycle are distinct from descriptive identity. Never infer active from identity.
    active_items=_matching(evidence,'lifecycle',PlaceLifecycle.ACTIVE)
    existence_items=_matching(evidence,'existence',True)
    life_lineages=_trusted_lineages(active_items) | _trusted_lineages(existence_items)
    if place.lifecycle is not PlaceLifecycle.ACTIVE:
        reasons.append('canonical lifecycle is not active')
    if not life_lineages:
        reasons.append('no trusted explicit existence/lifecycle evidence')
    for field in OPTIONAL_FIELDS:
        value=getattr(place,field)
        if value in (None,''): continue
        items=_matching(evidence,field,value)
        if _trusted_lineages(items) and not _has_conflict(evidence,field,value):
            optional.append(field)
    outcome='eligible' if not reasons else ('needs_lifecycle' if set(supported)==set(CORE_FIELDS) and all(r in {'canonical lifecycle is not active','no trusted explicit existence/lifecycle evidence'} for r in reasons) else 'review')
    return ConfidenceDecision(place.identity.place_id,place.canonical_name,outcome,tuple(reasons),tuple(supported),tuple(optional),len(life_lineages))


def audit_database(database_path: str|Path, province='ปราจีนบุรี', pilot_limit=20):
    places, by_place=_load_places_and_evidence(database_path,province)
    decisions=[evaluate_place(p,by_place.get(p.identity.place_id,())) for p in places]
    counts=Counter(d.outcome for d in decisions)
    reasons=Counter(r for d in decisions for r in d.reasons)
    pilots=sorted((d for d in decisions if d.outcome=='needs_lifecycle'), key=lambda d:(-len(d.core_supported),d.name.casefold(),d.place_id))[:pilot_limit]
    return {
      'province':province,'canonical_count':len(places),'outcome_counts':sorted(counts.items()),
      'reason_counts':sorted(reasons.items()),'pilot_candidates':[d.__dict__ for d in pilots],
      'policy_version':POLICY_VERSION,'mode':'READ_ONLY','canonical_writes':False,
      'publication_performed':False,'user_web_switched':False,
    }
