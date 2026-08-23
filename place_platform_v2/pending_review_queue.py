from __future__ import annotations
import hashlib, json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION='4.8-pending-review-queue-v1'
_NAMESPACE=uuid.UUID('8bd01d2c-bd0c-4c16-9aa1-d975699d5b83')
SCHEMA='''CREATE TABLE IF NOT EXISTS precanonical_pending_review (
 queue_id TEXT PRIMARY KEY,
 candidate_id TEXT NOT NULL UNIQUE REFERENCES precanonical_candidates(candidate_id) ON DELETE RESTRICT,
 reason TEXT NOT NULL,
 current_state TEXT NOT NULL,
 next_action TEXT NOT NULL,
 status TEXT NOT NULL,
 source_policy_version TEXT,
 payload_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
)'''

def _load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def _qid(candidate_id): return str(uuid.uuid5(_NAMESPACE,'pending|'+candidate_id))
def _snapshot(con, exclude=()):
    names=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name") if r[0] not in exclude]
    return {n:[tuple(x) for x in con.execute(f'SELECT * FROM "{n}" ORDER BY rowid')] for n in names}

def queue_pending_reviews(*,database_path,adoption_report_path,lifecycle_report_path,direct_confirmation_report_path,coverage_report_path,commit=False,now=None)->dict[str,Any]:
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    adoption=_load(adoption_report_path); lifecycle=_load(lifecycle_report_path); direct=_load(direct_confirmation_report_path); coverage=_load(coverage_report_path)
    con=sqlite3.connect(Path(database_path)); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON')
    before=_snapshot(con,('precanonical_pending_review',))
    lifecycle_by_id={d.get('candidate_id'):d for d in lifecycle.get('decisions',[])}
    pending=[]
    for d in adoption.get('decisions',[]):
        if d.get('adoption_outcome')!='NEEDS_REVIEW': continue
        cid=d.get('candidate_id'); life=lifecycle_by_id.get(cid,{})
        if life.get('resolution_outcome')!='UNRESOLVED_NEEDS_DIRECT_CONFIRMATION': continue
        same_direct=(direct.get('candidate_name')==d.get('name') and direct.get('province')==d.get('province'))
        if same_direct and direct.get('confirmation_outcome') in {'CONFIRMED_OPEN','CONFIRMED_CLOSED'}: continue
        pending.append({
          'candidate_id':cid,'candidate_key':d.get('candidate_key'),'name':d.get('name'),'province':d.get('province'),'category':d.get('category'),
          'reason':'unresolved_lifecycle_conflict','current_state':'STILL_UNRESOLVED' if same_direct else life.get('resolution_outcome','NEEDS_REVIEW'),
          'next_action':'supply_valid_direct_confirmation','review_flags':d.get('review_flags') or [],
          'source_policy_version':life.get('policy_version') or lifecycle.get('policy_version')
        })
    inserted=updated=already=0
    if commit:
        con.execute('BEGIN'); con.execute(SCHEMA)
        for item in pending:
            qid=_qid(item['candidate_id']); payload=json.dumps(item,ensure_ascii=False,sort_keys=True)
            row=con.execute('select reason,current_state,next_action,status,payload_json from precanonical_pending_review where candidate_id=?',(item['candidate_id'],)).fetchone()
            vals=(item['reason'],item['current_state'],item['next_action'],'pending_manual_confirmation',payload)
            if row is None:
                con.execute('''insert into precanonical_pending_review(queue_id,candidate_id,reason,current_state,next_action,status,source_policy_version,payload_json,created_at,updated_at) values(?,?,?,?,?,?,?,?,?,?)''',
                    (qid,item['candidate_id'],*vals[:4],item['source_policy_version'],payload,now.isoformat(),now.isoformat())); inserted+=1
            elif tuple(row)==vals:
                already+=1
            else:
                con.execute('''update precanonical_pending_review set reason=?,current_state=?,next_action=?,status=?,source_policy_version=?,payload_json=?,updated_at=? where candidate_id=?''',
                    (item['reason'],item['current_state'],item['next_action'],'pending_manual_confirmation',item['source_policy_version'],payload,now.isoformat(),item['candidate_id'])); updated+=1
        con.commit()
    queue_total=con.execute("select count(*) from precanonical_pending_review where status='pending_manual_confirmation'").fetchone()[0] if commit else len(pending)
    after=_snapshot(con,('precanonical_pending_review',))
    # Coverage work is deliberately independent of the manual-review queue.
    next_work=coverage.get('next_recommended_work')
    if next_work and any(p.get('province')==next_work.get('province') and p.get('category')==next_work.get('category') for p in pending):
        # A pending individual candidate does not block category discovery; record that explicitly.
        next_work=dict(next_work); next_work['pending_candidates_do_not_block_discovery']=True
    con.close()
    return {'status':'PASS','mode':'COMMIT' if commit else 'DRY_RUN','policy_version':POLICY_VERSION,
      'pending_candidate_count':len(pending),'pending_candidates':pending,'inserted_queue_count':inserted,'updated_queue_count':updated,
      'already_queued_count':already,'pending_queue_total':queue_total,'next_discovery_work':next_work,
      'discovery_continues':next_work is not None,
      'safety':{'non_queue_tables_unchanged':before==after,'canonical_writes':False,'canonical_evidence_writes':False,
        'precanonical_identity_or_evidence_writes':False,'production_json_writes':False,'automatic_adoption':False,
        'automatic_publication':False,'pending_candidate_blocks_discovery':False,'trust_policy_lowered':False,'idempotent_queue':True}}
