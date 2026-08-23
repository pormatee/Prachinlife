from __future__ import annotations
import json, sqlite3, uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION='5-final-operational-work-queue-v1'
_NAMESPACE=uuid.UUID('8e949d75-84f1-4894-9708-c2e2fc9350f4')
SCHEMA='''CREATE TABLE IF NOT EXISTS operational_work_queue (
 work_id TEXT PRIMARY KEY,
 work_key TEXT NOT NULL UNIQUE,
 candidate_id TEXT,
 name TEXT NOT NULL,
 province TEXT NOT NULL,
 category TEXT NOT NULL,
 queue_type TEXT NOT NULL,
 next_action TEXT NOT NULL,
 blockers_json TEXT NOT NULL,
 status TEXT NOT NULL,
 first_seen_at TEXT NOT NULL,
 last_seen_at TEXT NOT NULL,
 resolved_at TEXT,
 payload_json TEXT NOT NULL
)'''

def _key(item, province, category):
    cid=str(item.get('candidate_id') or '').strip()
    ident=cid or str(item.get('name') or '').strip().casefold()
    return f'{province}|{category}|{ident}'

def _wid(key): return str(uuid.uuid5(_NAMESPACE,key))

def sync_operational_work_queue(*, database_path:str|Path, work_items:list[dict[str,Any]], province:str, category:str, commit:bool=False, now=None)->dict[str,Any]:
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    ts=now.isoformat(); db=Path(database_path)
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    exists=con.execute("select 1 from sqlite_master where type='table' and name='operational_work_queue'").fetchone() is not None
    active=[]
    for item in work_items:
        if item.get('queue')=='excluded_non_primary': continue
        x=dict(item); x['work_key']=_key(x,province,category); active.append(x)
    inserted=updated=unchanged=resolved=0
    if commit:
        con.execute('BEGIN'); con.execute(SCHEMA)
        current={r['work_key']:dict(r) for r in con.execute("select * from operational_work_queue where province=? and category=? and status='OPEN'",(province,category))}
        seen=set()
        for item in active:
            key=item['work_key']; seen.add(key); payload=json.dumps(item,ensure_ascii=False,sort_keys=True); blockers=json.dumps(item.get('blockers') or [],ensure_ascii=False,sort_keys=True)
            row=con.execute('select * from operational_work_queue where work_key=?',(key,)).fetchone()
            if row is None:
                con.execute('''insert into operational_work_queue(work_id,work_key,candidate_id,name,province,category,queue_type,next_action,blockers_json,status,first_seen_at,last_seen_at,resolved_at,payload_json) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(_wid(key),key,item.get('candidate_id'),item['name'],province,category,item['queue'],item['next_action'],blockers,'OPEN',ts,ts,None,payload)); inserted+=1
            else:
                changed=(row['queue_type']!=item['queue'] or row['next_action']!=item['next_action'] or row['blockers_json']!=blockers or row['status']!='OPEN')
                if changed:
                    con.execute('''update operational_work_queue set candidate_id=?,name=?,queue_type=?,next_action=?,blockers_json=?,status='OPEN',last_seen_at=?,resolved_at=NULL,payload_json=? where work_key=?''',(item.get('candidate_id'),item['name'],item['queue'],item['next_action'],blockers,ts,payload,key)); updated+=1
                else:
                    unchanged+=1
        for key in set(current)-seen:
            con.execute("update operational_work_queue set status='RESOLVED',last_seen_at=?,resolved_at=? where work_key=?",(ts,ts,key)); resolved+=1
        con.commit(); exists=True
    rows=[]
    if exists:
        rows=[dict(r) for r in con.execute("select work_id,work_key,candidate_id,name,province,category,queue_type,next_action,status,first_seen_at,last_seen_at,resolved_at from operational_work_queue where province=? and category=? order by status,queue_type,name",(province,category))]
    con.close()
    open_rows=[r for r in rows if r['status']=='OPEN'] if commit else [{**x,'status':'OPEN'} for x in active]
    counts=Counter(r.get('queue_type',r.get('queue')) for r in open_rows)
    return {'status':'PASS','mode':'COMMIT' if commit else 'DRY_RUN','policy_version':POLICY_VERSION,'scope':{'province':province,'category':category},'active_work_count':len(active),'open_queue_count':len(open_rows),'queue_counts':dict(sorted(counts.items())),'inserted':inserted,'updated':updated,'unchanged':unchanged,'resolved':resolved,'open_work':open_rows,'safety':{'queue_only_write':True,'canonical_writes':False,'precanonical_writes':False,'production_json_writes':False,'automatic_adoption':False,'trust_policy_lowered':False,'idempotent':True}}
