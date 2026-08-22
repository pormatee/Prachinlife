from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .publication_readiness import _REQUIRED, evidence_lineage_key
from .sqlite_store import SQLitePlaceRepository

POLICY_VERSION = '2W.7-evidence-trust-calibration-v1'
_OSM = re.compile(r'(?:openstreetmap\.org/|osm[-:/ ]*)(?:node|way|relation)[-:/ ]*\d+', re.I)


def _text(*values) -> str:
    return ' '.join(str(v) for v in values if v is not None)


def classify_evidence(evidence) -> str:
    md = dict(evidence.metadata or {})
    source_name = (evidence.source.source_name or '').strip().casefold()
    source_url = evidence.source.source_url or ''
    source_record = evidence.source.source_record_id or ''
    underlying = _text(md.get('underlying_seed_source_url'), md.get('underlying_seed_source_name'))
    if source_name == 'prachinlife admin operator' or md.get('provenance_origin') == 'operator_change':
        return 'admin_operator'
    if source_name == 'openstreetmap' or 'openstreetmap.org' in source_url.casefold():
        return 'direct_osm'
    if source_name == 'prachinlife-v1-json' and _OSM.search(source_record):
        return 'v1_derived_osm'
    if _OSM.search(underlying):
        return 'derived_from_osm'
    if source_url.startswith(('http://','https://')) and 'openstreetmap.org' not in source_url.casefold():
        return 'independent_web'
    return 'legacy_unknown'


def _value_key(value) -> str:
    if hasattr(value, 'latitude') and hasattr(value, 'longitude'):
        return f'{value.latitude:.7f},{value.longitude:.7f}'
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


@dataclass(frozen=True)
class CalibratedPlace:
    place_id: str
    canonical_name: str
    province: str | None
    lifecycle: str
    evidence_count: int
    evidence_field_count: int
    lineage_count: int
    trusted_lineage_count: int
    required_lineage_min: int
    missing_required_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...]
    trust_classes: tuple[tuple[str,int], ...]
    pilot_score: int


@dataclass(frozen=True)
class CalibrationReport:
    province: str
    canonical_count: int
    evidence_count: int
    trust_class_counts: tuple[tuple[str,int], ...]
    lineage_count: int
    places_with_multiple_lineages: int
    places_with_conflicts: int
    lifecycle_active_count: int
    readiness_shape_counts: tuple[tuple[str,int], ...]
    pilot_candidates: tuple[CalibratedPlace, ...]
    policy_version: str = POLICY_VERSION
    mode: str = 'READ_ONLY'
    canonical_writes: bool = False
    publication_performed: bool = False
    user_web_switched: bool = False


def _load(database_path: str | Path, province: str):
    db=Path(database_path).resolve()
    con=sqlite3.connect(f'{db.as_uri()}?mode=ro', uri=True); con.row_factory=sqlite3.Row
    try:
        prows=con.execute('SELECT * FROM places WHERE province=? ORDER BY place_id',(province,)).fetchall()
        ids=[r['place_id'] for r in prows]
        if not ids: return (),{}
        q=','.join('?' for _ in ids)
        erows=con.execute(f'SELECT * FROM place_evidence WHERE place_id IN ({q}) ORDER BY place_id,evidence_id',ids).fetchall()
    finally: con.close()
    places=tuple(SQLitePlaceRepository._place_from_row(r) for r in prows)
    by=defaultdict(list)
    for r in erows:
        e=SQLitePlaceRepository._evidence_from_row(r); by[e.place_id].append(e)
    return places,{k:tuple(v) for k,v in by.items()}


def calibrate_evidence_trust(database_path: str | Path, *, province: str='ปราจีนบุรี', pilot_limit: int=20):
    places, by = _load(database_path, province)
    class_counts=Counter(); global_lineages=set(); rows=[]; multi=conflicted=active=0; shapes=Counter(); total_ev=0
    trusted_classes={'direct_osm','admin_operator','independent_web'}
    for p in places:
        ev=by.get(p.identity.place_id,()); total_ev += len(ev)
        classes=Counter(classify_evidence(e) for e in ev); class_counts.update(classes)
        lineages={evidence_lineage_key(e) for e in ev}; global_lineages.update(lineages)
        if len(lineages)>1: multi+=1
        trusted={evidence_lineage_key(e) for e in ev if classify_evidence(e) in trusted_classes}
        fields={e.field_name for e in ev}
        missing=[]; conflicts=[]; req_counts=[]
        for field in _REQUIRED:
            vals=defaultdict(set)
            for e in ev:
                if e.field_name==field and e.status.value not in {'rejected','stale'}:
                    vals[_value_key(e.value)].add(evidence_lineage_key(e))
            canonical=_value_key(getattr(p,field))
            count=len(vals.get(canonical,set())); req_counts.append(count)
            if count==0: missing.append(field)
            if any(k != canonical for k in vals): conflicts.append(field)
        if conflicts: conflicted+=1
        if p.lifecycle.value=='active': active+=1
        req_min=min(req_counts) if req_counts else 0
        if conflicts: shape='conflict_review'
        elif missing: shape='missing_canonical_evidence'
        elif req_min>=2 and p.lifecycle.value=='active': shape='lineage_ready_shape'
        elif req_min>=2: shape='needs_lifecycle_state'
        elif req_min==1: shape='needs_one_more_lineage'
        else: shape='needs_full_verification'
        shapes[shape]+=1
        # Ranking only prioritizes evidence already present; it never grants verification.
        score=(req_min*100 + len(trusted)*20 + len(lineages)*10 + len(fields)*2 + min(len(ev),20)
               - len(missing)*80 - len(conflicts)*150 - (0 if p.lifecycle.value=='active' else 15))
        rows.append(CalibratedPlace(p.identity.place_id,p.canonical_name,p.province,p.lifecycle.value,len(ev),len(fields),len(lineages),len(trusted),req_min,tuple(missing),tuple(conflicts),tuple(sorted(classes.items())),score))
    pilots=tuple(sorted(rows,key=lambda r:(bool(r.conflict_fields),-r.pilot_score,-r.trusted_lineage_count,-r.lineage_count,r.canonical_name.casefold(),r.place_id))[:pilot_limit])
    report=CalibrationReport(province,len(places),total_ev,tuple(sorted(class_counts.items())),len(global_lineages),multi,conflicted,active,tuple(sorted(shapes.items())),pilots)
    return report, tuple(rows)


def database_sha256(path: str | Path) -> str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def report_as_dict(report: CalibrationReport):
    return asdict(report)
