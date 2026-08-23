from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION='4.17-identity-evidence-followup-v1'

def _load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _norm(v): return re.sub(r'[^0-9a-zก-๙]+','',str(v or '').casefold())

def _match(name, obs):
    a=_norm(name); b=_norm(obs.get('name') or obs.get('candidate_name') or obs.get('observed_name'))
    return bool(a and b and (a==b or a in b or b in a))

def followup_identity_evidence(*, batch_report_path, observations_path, database_path=None)->dict[str,Any]:
    batch=_load(batch_report_path); obs=_load(observations_path)
    target=next((x for x in batch.get('results',[]) if x.get('name')=='ฉันทนา'),None)
    if target is None: raise ValueError('known candidate ฉันทนา not found')
    rows=[x for x in obs if _match(target['name'],x) and x.get('province')==target.get('province')]
    accepted=[]
    for x in rows:
        accepted.append(dict(x))
    # Different hosts/families are not automatically independent when they reproduce the same report.
    origin_groups={}
    for x in accepted:
        key=str(x.get('editorial_origin') or x.get('syndication_group') or x.get('source_family') or '').strip().casefold()
        origin_groups.setdefault(key,[]).append(x.get('source_family'))
    independent_origins=[k for k in origin_groups if k]
    source_families=sorted({str(x.get('source_family') or '').strip().casefold() for x in accepted if x.get('source_family')})
    if len(independent_origins)>=2:
        outcome='VERIFIED_IDENTITY'
        next_step='acquire_geolocation_and_persist_precanonical_evidence'
    elif independent_origins:
        outcome='SUPPORTED_IDENTITY'
        next_step='acquire_truly_independent_source_not_syndicated_copy'
    else:
        outcome='INSUFFICIENT_EVIDENCE'
        next_step='acquire_independent_source'
    return {
      'status':'PASS','policy_version':POLICY_VERSION,'candidate':target['name'],'province':target.get('province'),
      'raw_observation_count':len(accepted),'raw_source_family_count':len(source_families),'source_families':source_families,
      'independent_editorial_origin_count':len(independent_origins),'editorial_origins':independent_origins,
      'identity_outcome':outcome,'next_step':next_step,'canonical_ready':False,
      'quality':{'syndicated_copies_not_counted_as_independent':True,'host_count_not_equal_independence':True},
      'safety':{'database_unchanged':True,'canonical_writes':False,'precanonical_writes':False,'pending_queue_writes':False,
                'production_json_writes':False,'automatic_adoption':False,'trust_policy_lowered':False}
    }
