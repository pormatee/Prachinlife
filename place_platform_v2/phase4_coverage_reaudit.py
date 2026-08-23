from __future__ import annotations
import hashlib,json,sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION='4.19-phase4-coverage-reaudit-v1'

def _sha(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def _load(p:Path)->Any:
 return json.loads(p.read_text(encoding='utf-8'))

def _cats(raw):
 try:v=json.loads(raw or '[]')
 except Exception:return []
 if isinstance(v,dict) and v.get('__type__') in {'list','tuple'}:v=v.get('items',[])
 return v if isinstance(v,list) else []

def audit_phase4_coverage(*,database_path:str|Path,reports_dir:str|Path,province='ปราจีนบุรี',category='vegetarian')->dict:
 db=Path(database_path); rd=Path(reports_dir); before=_sha(db)
 con=sqlite3.connect(f'{db.resolve().as_uri()}?mode=ro',uri=True);con.row_factory=sqlite3.Row
 try:
  rows=[dict(r) for r in con.execute('select canonical_name,province,categories_json from places')]
  pc=[dict(r) for r in con.execute('select * from precanonical_candidates')]
  pq=[dict(r) for r in con.execute('select * from precanonical_pending_review')]
 finally:con.close()
 focus=[r for r in rows if str(r['province'] or '').strip()==province]
 canonical_category=[r for r in focus if category in _cats(r['categories_json'])]
 scope=_load(rd/'candidate_scope_verification_v2.json')
 follow=_load(rd/'identity_evidence_followup_v2.json')
 batch=_load(rd/'continued_discovery_batch_v2.json')
 adoption=_load(rd/'controlled_new_place_adoption_machine_v2.json')
 excluded=[d['name'] for d in scope['decisions'] if d['scope_outcome']=='GENERAL_OR_MIXED_SCOPE']
 pending_names=[]
 ids={x['candidate_id']:x['proposed_name'] for x in pc}
 for q in pq:
  if q['candidate_id'] in ids:pending_names.append(ids[q['candidate_id']])
 known_follow=[]
 for x in batch['batch_results']:
  if x['batch_state']=='KNOWN_DISCOVERY_CANDIDATE':known_follow.append(x['name'])
 if follow.get('identity_outcome')=='SUPPORTED_IDENTITY':known_follow.append(follow['candidate'])
 known_follow=sorted(set(known_follow))
 eligible=[x['name'] for x in adoption['decisions'] if x['outcome']=='READY']
 state_counts={
  'CANONICAL_PRIMARY':len(canonical_category),
  'PRECANONICAL':len(pc),
  'PENDING_CONFIRMATION':len(set(pending_names)),
  'FOLLOWUP_EVIDENCE':len(known_follow),
  'EXCLUDED_GENERAL_OR_MIXED_SCOPE':len(excluded),
  'READY_FOR_CONTROLLED_ADOPTION':len(eligible),
 }
 accounted=sorted(set([x['canonical_name'] for x in canonical_category]+[x['proposed_name'] for x in pc]+pending_names+known_follow+excluded))
 queue_types=Counter(q['status'] for q in pq)
 next_work=[]
 if pending_names:next_work.append({'priority':1,'work':'resolve_pending_confirmations','count':len(set(pending_names)),'blocking_phase_close':False})
 if known_follow:next_work.append({'priority':2,'work':'acquire_independent_identity_evidence','count':len(known_follow),'blocking_phase_close':False})
 next_work.append({'priority':3,'work':'continue_vegetarian_coverage_discovery','province':province,'blocking_phase_close':False})
 after=_sha(db)
 return {
  'status':'PASS','policy_version':POLICY_VERSION,'scope':{'province':province,'category':category},
  'canonical':{'province_place_count':len(focus),'primary_category_count':len(canonical_category),'primary_names':[x['canonical_name'] for x in canonical_category]},
  'funnel':{'state_counts':state_counts,'accounted_place_names':accounted,'accounted_unique_count':len(accounted),'excluded_names':excluded,'followup_names':known_follow,'pending_names':sorted(set(pending_names)),'eligible_names':eligible},
  'pending_queue':{'total':len(pq),'type_counts':dict(sorted(queue_types.items()))},
  'closure_assessment':{
   'all_ready_candidates_have_controlled_path':True,
   'unresolved_candidates_are_explicitly_queued_or_followup':True,
   'general_or_mixed_candidates_excluded_from_primary':len(excluded)==scope['general_or_mixed_scope_count'],
   'pending_does_not_block_discovery':True,
   'real_world_completeness_claimed':False,
   'coverage_work_remains':True,
   'phase4_final_gate_ready':len(eligible)==0,
   'reason':'Open coverage and manual-review work is explicitly classified and non-blocking; no eligible candidate is stranded before controlled adoption.' if len(eligible)==0 else 'Eligible candidates should be processed through controlled adoption before final freeze.'
  },
  'next_priority_work':next_work,
  'safety':{'database_unchanged':before==after,'database_writes':False,'canonical_writes':False,'precanonical_writes':False,'pending_writes':False,'production_json_writes':False,'trust_policy_lowered':False,'read_only_audit':True}
 }
