from __future__ import annotations
import hashlib,json,re,sqlite3,uuid
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

POLICY_VERSION='4.18-controlled-new-place-adoption-machine-v1'
_NAMESPACE=uuid.UUID('a691ef73-c45b-4c48-8b43-52355cf807bd')

def _norm(v): return re.sub(r'[\W_]+','',str(v or '').casefold(),flags=re.UNICODE)
def _phone(v):
 d=re.sub(r'\D+','',str(v or ''))
 return '0'+d[2:] if d.startswith('66') and len(d)>=10 else d

def _payload(e):
 try:return json.loads(e['payload_json'] or '{}')
 except Exception:return {}

def _coords(evidence):
 vals=[]
 for e in evidence:
  p=_payload(e); lat=p.get('latitude');lon=p.get('longitude')
  if lat is None or lon is None:continue
  if p.get('coordinate_owner') not in (None,'candidate'):continue
  if e['evidence_kind'] not in ('candidate_address_location','direct_coordinate_confirmation','exact_candidate_coordinates'):continue
  try: vals.append((float(lat),float(lon),e['evidence_id']))
  except (TypeError,ValueError):pass
 return vals

def _snapshot(con):
 names=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
 return {n:[tuple(x) for x in con.execute(f'SELECT * FROM "{n}" ORDER BY rowid')] for n in names}

def _pid(candidate_id): return str(uuid.uuid5(_NAMESPACE,'place|'+candidate_id))
def _eid(candidate_id,source_eid,field): return str(uuid.uuid5(_NAMESPACE,f'evidence|{candidate_id}|{source_eid}|{field}'))
def _rid(candidate_id): return str(uuid.uuid5(_NAMESPACE,'revision|'+candidate_id))

def evaluate_new_place_adoption(*,database_path)->dict[str,Any]:
 con=sqlite3.connect(Path(database_path));con.row_factory=sqlite3.Row
 before=_snapshot(con); decisions=[];counts=Counter()
 candidates=[dict(r) for r in con.execute('select * from precanonical_candidates order by candidate_id')]
 pending_ids=set()
 if con.execute("select 1 from sqlite_master where type='table' and name='precanonical_pending_review'").fetchone():
  pending_ids={r[0] for r in con.execute("select candidate_id from precanonical_pending_review")}
 for c in candidates:
  ev=[dict(r) for r in con.execute('select * from precanonical_evidence where candidate_id=? order by evidence_id',(c['candidate_id'],))]
  fam={str(x['source_family']).strip().casefold() for x in ev if x['source_family']}
  conflicts=json.loads(c['lifecycle_conflict_json'] or '[]'); coords=_coords(ev)
  duplicate=[]
  for p in con.execute('select place_id,canonical_name,province,phone from places'):
   if (_norm(p['canonical_name'])==_norm(c['proposed_name']) and str(p['province'] or '').strip()==str(c['province'] or '').strip()) or (_phone(p['phone']) and any(_phone(x['phone'])==_phone(p['phone']) for x in ev if _phone(x['phone']))): duplicate.append(p['place_id'])
  blockers=[]
  if c['identity_outcome']!='VERIFIED_IDENTITY':blockers.append('identity_not_verified')
  if len(fam)<2:blockers.append('insufficient_independent_identity_sources')
  if conflicts:blockers.append('unresolved_lifecycle_conflict')
  if c['candidate_id'] in pending_ids:blockers.append('pending_manual_or_coordinate_confirmation')
  if not coords:blockers.append('exact_candidate_coordinates_not_verified')
  if duplicate:blockers.append('canonical_duplicate_risk')
  if blockers: outcome='NOT_READY';next_step='resolve_adoption_blockers'
  else: outcome='READY';next_step='controlled_commit'
  counts[outcome]+=1
  decisions.append({'candidate_id':c['candidate_id'],'name':c['proposed_name'],'province':c['province'],'category':c['category'],'outcome':outcome,'blockers':blockers,'source_family_count':len(fam),'exact_coordinate_count':len(coords),'duplicate_place_ids':duplicate,'next_step':next_step})
 after=_snapshot(con);con.close()
 return {'status':'PASS','policy_version':POLICY_VERSION,'candidate_count':len(candidates),'decision_counts':dict(sorted(counts.items())),'ready_count':counts['READY'],'not_ready_count':counts['NOT_READY'],'decisions':decisions,'safety':{'database_unchanged':before==after,'production_json_writes':False,'automatic_publication':False,'trust_policy_lowered':False}}

def run_controlled_new_place_adoption(*,database_path,commit=False,adopted_at=None)->dict[str,Any]:
 adopted_at=adopted_at or datetime.now(timezone.utc)
 if adopted_at.tzinfo is None:raise ValueError('adopted_at must be timezone-aware')
 db=Path(database_path); evaluation=evaluate_new_place_adoption(database_path=db); ready=[x for x in evaluation['decisions'] if x['outcome']=='READY']
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.execute('pragma foreign_keys=on'); before=_snapshot(con)
 inserted_places=inserted_evidence=inserted_revisions=0
 if commit and ready:
  con.execute('BEGIN IMMEDIATE')
  for d in ready:
   c=dict(con.execute('select * from precanonical_candidates where candidate_id=?',(d['candidate_id'],)).fetchone()); ev=[dict(r) for r in con.execute('select * from precanonical_evidence where candidate_id=? order by evidence_id',(d['candidate_id'],))]
   coords=_coords(ev); lat,lon,_=coords[0]; pid=_pid(c['candidate_id']); now=adopted_at.isoformat()
   phones=Counter(_phone(x['phone']) for x in ev if _phone(x['phone'])); phone=phones.most_common(1)[0][0] if phones else None
   addresses=[_payload(x).get('address_text') for x in ev if _payload(x).get('address_text')]; address=addresses[0] if addresses else None
   life=Counter(str(x['lifecycle_status']).casefold() for x in ev if x['lifecycle_status']); lifecycle='active' if life.get('open') else 'unknown'
   cur=con.execute('insert or ignore into places values(?,?,?,?,?,?,?,?,?,?,?,?)',(pid,c['proposed_name'],lat,lon,address,c['province'],json.dumps([c['category']],ensure_ascii=False),phone,None,lifecycle,now,now)); inserted_places+=max(cur.rowcount,0)
   for x in ev:
    claims=[('canonical_name',c['proposed_name'],'name'),('province',c['province'],'other')]
    if x.get('phone'):claims.append(('phone',_phone(x['phone']),'contact'))
    p=_payload(x)
    if p.get('latitude') is not None and p.get('longitude') is not None and p.get('coordinate_owner') in (None,'candidate'):claims.append(('location',{'latitude':p['latitude'],'longitude':p['longitude']},'location'))
    for field,val,kind in claims:
     eid=_eid(c['candidate_id'],x['evidence_id'],field)
     cur=con.execute('''insert or ignore into place_evidence(evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json) values(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(eid,pid,x['source_type'],x['source_name'],x['source_record_id'],x['source_url'],x['created_at'],kind,field,json.dumps(val,ensure_ascii=False),'supported',now,json.dumps({'precanonical_evidence_id':x['evidence_id'],'source_family':x['source_family']},ensure_ascii=False))); inserted_evidence+=max(cur.rowcount,0)
   rid=_rid(c['candidate_id']); cur=con.execute('''insert or ignore into place_revisions(revision_id,place_id,changed_fields_json,before_values_json,after_values_json,reason,evidence_ids_json,policy_version,created_at) values(?,?,?,?,?,?,?,?,?)''',(rid,pid,json.dumps(['create_place']),json.dumps({}),json.dumps({'canonical_name':c['proposed_name'],'province':c['province']} ,ensure_ascii=False),'Phase 4.18 controlled new place adoption',json.dumps([x['evidence_id'] for x in ev]),POLICY_VERSION,now));inserted_revisions+=max(cur.rowcount,0)
   con.execute("update precanonical_candidates set status='adopted_canonical',policy_version=? where candidate_id=?",(POLICY_VERSION,c['candidate_id']))
  con.commit()
 after=_snapshot(con);con.close()
 return {'status':'PASS','mode':'COMMIT' if commit else 'DRY_RUN','policy_version':POLICY_VERSION,'eligible_count':len(ready),'inserted_place_count':inserted_places,'inserted_evidence_count':inserted_evidence,'inserted_revision_count':inserted_revisions,'decisions':evaluation['decisions'],'safety':{'database_unchanged':before==after,'production_json_writes':False,'automatic_publication':False,'trust_policy_lowered':False,'commit_requires_full_eligibility':True}}
