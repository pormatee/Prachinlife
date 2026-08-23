from __future__ import annotations

import hashlib, json, sqlite3, uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical_adoption_review import review_controlled_canonical_adoption

POLICY_VERSION = "3.7-explicit-controlled-canonical-adoption-v1"
_NAMESPACE = uuid.UUID("65a4721a-f638-49c1-923b-c89fc03d2ebf")
ALLOWED_FIELDS = frozenset({"phone", "website"})


def _sha256(path: str | Path) -> str:
    h=hashlib.sha256();
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()


def _snap(con: sqlite3.Connection, exclude=()) -> dict[str,list[tuple[Any,...]]]:
    names=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name") if r[0] not in set(exclude)]
    return {n:[tuple(x) for x in con.execute(f'SELECT * FROM "{n}" ORDER BY rowid')] for n in names}


def _revision_id(d: dict[str,Any]) -> str:
    material="|".join([str(d['place_id']),str(d['field_name']),str(d['proposed_value']),*sorted(map(str,d.get('evidence_ids',())))])
    return str(uuid.uuid5(_NAMESPACE,material))


def apply_controlled_canonical_adoption(*, database_path: str|Path, commit: bool=False, applied_at: datetime|None=None) -> dict[str,Any]:
    """Explicitly apply Phase 3.6 proposals to canonical contact fields.

    Recomputes the review from current evidence before applying. Only `places.phone`,
    `places.website`, `places.updated_at`, and append-only `place_revisions` may change.
    Production JSON is never written here.
    """
    applied_at=applied_at or datetime.now(timezone.utc)
    if applied_at.tzinfo is None: raise ValueError("applied_at must be timezone-aware")
    db=Path(database_path)
    review=review_controlled_canonical_adoption(database_path=db)
    review_decisions=list(review['decisions'])

    con=sqlite3.connect(db); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON')
    before_hash=_sha256(db); before_other=_snap(con,exclude=('places','place_revisions'))
    proposals=[]
    for d in review_decisions:
        if d.get('adoption_outcome')=='proposed':
            proposals.append(d)
        elif d.get('adoption_outcome')=='no_change':
            rid=_revision_id(d)
            if con.execute('select 1 from place_revisions where revision_id=?',(rid,)).fetchone():
                proposals.append(d)
    before_evidence=[tuple(r) for r in con.execute('select * from place_evidence order by rowid')]
    counts=Counter(); decisions=[]

    # Preflight all proposals before beginning a write transaction.
    for d in proposals:
        field=str(d.get('field_name') or '')
        if field not in ALLOWED_FIELDS:
            counts['blocked']+=1; decisions.append({**d,'apply_outcome':'blocked','reason':'field_not_allowed'}); continue
        row=con.execute(f'SELECT {field} FROM places WHERE place_id=?',(d['place_id'],)).fetchone()
        if row is None:
            counts['blocked']+=1; decisions.append({**d,'apply_outcome':'blocked','reason':'canonical_place_missing'}); continue
        current=row[field]
        if current != d.get('current_value') and current != d.get('proposed_value'):
            counts['blocked']+=1; decisions.append({**d,'apply_outcome':'blocked','reason':'canonical_value_changed_since_review'}); continue
        ev_ids=list(d.get('evidence_ids') or [])
        if not ev_ids:
            counts['blocked']+=1; decisions.append({**d,'apply_outcome':'blocked','reason':'missing_evidence_ids'}); continue
        placeholders=','.join('?' for _ in ev_ids)
        ev=con.execute(f'SELECT evidence_id,status,value_json FROM place_evidence WHERE evidence_id IN ({placeholders})',ev_ids).fetchall()
        if len(ev)!=len(ev_ids) or any(r['status'] in ('rejected','stale') for r in ev):
            counts['blocked']+=1; decisions.append({**d,'apply_outcome':'blocked','reason':'evidence_not_active'}); continue
        outcome='already_applied' if current==d.get('proposed_value') else 'ready'
        counts[outcome]+=1; decisions.append({**d,'apply_outcome':outcome,'revision_id':_revision_id(d)})

    if counts['blocked']:
        con.close()
        return {'policy_version':POLICY_VERSION,'mode':'COMMIT' if commit else 'DRY_RUN','proposal_count':len(proposals),'apply_outcome_counts':dict(sorted(counts.items())),'decisions':decisions,'safety':{'transaction_committed':False,'database_unchanged':True,'evidence_unchanged':True,'non_adoption_tables_unchanged':True,'production_json_writes':False,'automatic_publication':False,'trust_policy_lowered':False,'province_agnostic':True}}

    inserted_revisions=0; updated_fields=0; already_present=0
    try:
        if commit:
            con.execute('BEGIN IMMEDIATE')
            for d in decisions:
                if d['apply_outcome']=='already_applied': already_present+=1; continue
                rid=d['revision_id']
                if con.execute('select 1 from place_revisions where revision_id=?',(rid,)).fetchone():
                    already_present+=1; continue
                field=d['field_name']; pid=d['place_id']; old=d.get('current_value'); new=d.get('proposed_value')
                con.execute(f'UPDATE places SET {field}=?, updated_at=? WHERE place_id=?',(new,applied_at.isoformat(),pid))
                con.execute('''INSERT INTO place_revisions(revision_id,place_id,changed_fields_json,before_values_json,after_values_json,reason,evidence_ids_json,policy_version,created_at) VALUES(?,?,?,?,?,?,?,?,?)''',(rid,pid,json.dumps([field]),json.dumps({field:old}),json.dumps({field:new}),"Phase 3.7 explicit controlled canonical adoption",json.dumps(d.get('evidence_ids') or []),POLICY_VERSION,applied_at.isoformat()))
                inserted_revisions+=1; updated_fields+=1
            con.commit()
    except Exception:
        con.rollback(); con.close(); raise

    after_other=_snap(con,exclude=('places','place_revisions'))
    after_evidence=[tuple(r) for r in con.execute('select * from place_evidence order by rowid')]
    con.close(); after_hash=_sha256(db)
    return {
      'policy_version':POLICY_VERSION,'mode':'COMMIT' if commit else 'DRY_RUN','proposal_count':len(proposals),
      'apply_outcome_counts':dict(sorted(counts.items())),'updated_field_count':updated_fields,'inserted_revision_count':inserted_revisions,'already_applied_count':already_present,'decisions':decisions,
      'safety':{'transaction_committed':bool(commit),'database_unchanged':before_hash==after_hash,'evidence_unchanged':before_evidence==after_evidence,'non_adoption_tables_unchanged':before_other==after_other,'production_json_writes':False,'automatic_publication':False,'trust_policy_lowered':False,'province_agnostic':True}
    }
