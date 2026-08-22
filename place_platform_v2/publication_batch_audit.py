from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .models import PlaceLifecycle
from .publication_readiness import _REQUIRED, lineage_source_count
from .sqlite_store import SQLitePlaceRepository
from .verification import VerificationPolicy

POLICY_VERSION = '2W.6-publication-batch-audit-v1'

@dataclass(frozen=True)
class PlaceReadinessRow:
    place_id: str
    canonical_name: str
    province: str | None
    lifecycle: str
    verified_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    blocker_count: int
    bucket: str

@dataclass(frozen=True)
class BatchAuditReport:
    canonical_count: int
    ready_count: int
    blocked_count: int
    bucket_counts: tuple[tuple[str,int], ...]
    field_block_counts: tuple[tuple[str,int], ...]
    province_counts: tuple[tuple[str,int], ...]
    pilot_candidates: tuple[PlaceReadinessRow, ...]
    policy_version: str = POLICY_VERSION
    mode: str = 'READ_ONLY'
    publication_performed: bool = False
    user_web_switched: bool = False


def _load_all(database_path: str | Path):
    db=Path(database_path).resolve()
    con=sqlite3.connect(f'{db.as_uri()}?mode=ro', uri=True)
    con.row_factory=sqlite3.Row
    try:
        prows=con.execute('SELECT * FROM places ORDER BY place_id').fetchall()
        erows=con.execute('SELECT * FROM place_evidence ORDER BY place_id,evidence_id').fetchall()
    finally:
        con.close()
    places=tuple(SQLitePlaceRepository._place_from_row(r) for r in prows)
    by={}
    for r in erows:
        e=SQLitePlaceRepository._evidence_from_row(r)
        by.setdefault(e.place_id,[]).append(e)
    return places,{k:tuple(v) for k,v in by.items()}


def _bucket(place, blocked: tuple[str,...]) -> str:
    if not blocked and place.lifecycle is PlaceLifecycle.ACTIVE:
        return 'ready'
    life=('lifecycle' in blocked) or place.lifecycle is not PlaceLifecycle.ACTIVE
    other=any(f != 'lifecycle' for f in blocked)
    if life and other: return 'needs_lifecycle_and_verification'
    if life: return 'needs_lifecycle'
    return 'needs_verification'


def audit_publication_readiness(database_path: str | Path, *, pilot_limit: int=20) -> tuple[BatchAuditReport, tuple[PlaceReadinessRow,...]]:
    places,by=_load_all(database_path)
    policy=VerificationPolicy()
    rows=[]; buckets=Counter(); fields=Counter(); provinces=Counter()
    for p in places:
        ev=by.get(p.identity.place_id,())
        verified=[]; blocked=[]
        for field in _REQUIRED:
            if lineage_source_count(ev,field,getattr(p,field)) >= policy.verified_independent_sources:
                verified.append(field)
            else:
                blocked.append(field); fields[field]+=1
        bucket=_bucket(p,tuple(blocked)); buckets[bucket]+=1
        provinces[p.province or '(missing)']+=1
        rows.append(PlaceReadinessRow(p.identity.place_id,p.canonical_name,p.province,p.lifecycle.value,tuple(verified),tuple(blocked),len(blocked),bucket))
    # Best pilot candidates first: ready, then fewest blockers; deterministic tie-break.
    rank={'ready':0,'needs_verification':1,'needs_lifecycle':2,'needs_lifecycle_and_verification':3}
    pilots=tuple(sorted(rows,key=lambda r:(rank[r.bucket],r.blocker_count,r.province or '',r.canonical_name,r.place_id))[:pilot_limit])
    ready=buckets['ready']
    report=BatchAuditReport(len(rows),ready,len(rows)-ready,tuple(sorted(buckets.items())),tuple(sorted(fields.items())),tuple(sorted(provinces.items())),pilots)
    return report,tuple(rows)
