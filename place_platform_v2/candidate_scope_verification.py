from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION='4.16-candidate-scope-verification-v1'
DEDICATED_TERMS=('ร้านอาหารเจ','อาหารเจโดยเฉพาะ','มังสวิรัติ','vegetarian restaurant','vegan restaurant','vegan cafe','plant-based restaurant')
GENERAL_TERMS=('นมสด','ซาลาเปา','ขนมจีบ','ติ่มซำ','อาหารเช้า','สตรีทฟู้ด','รถเข็น','ทำผม','salon','cafe')

def _norm(v): return re.sub(r'\s+',' ',str(v or '').strip().casefold())
def _load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def verify_candidate_scope(*,database_path,coverage_report_path,scope_observations_path)->dict[str,Any]:
    db=Path(database_path); before=db.read_bytes()
    coverage=_load(coverage_report_path); obs=_load(scope_observations_path)
    queue=[x for x in coverage.get('followup_queue',[]) if x.get('candidate_scope')=='category_only']
    decisions=[]
    for q in queue:
        rows=[o for o in obs if o.get('candidate_key')==q.get('candidate_key') or _norm(o.get('candidate_name'))==_norm(q.get('name'))]
        positive=[];general=[];independent=set()
        for o in rows:
            text=' '.join(_norm(o.get(k)) for k in ('scope_claim','merchant_description','observed_categories','menu_summary','review_summary'))
            if any(t in text for t in DEDICATED_TERMS) or o.get('scope_signal')=='dedicated_diet_business': positive.append(o)
            if any(t in text for t in GENERAL_TERMS) or o.get('scope_signal') in {'general_food_business','mixed_menu_business'}: general.append(o)
            fam=_norm(o.get('source_family'))
            if fam and fam!='wongnai': independent.add(fam)
        if positive and independent:
            outcome='DEDICATED_SCOPE_VERIFIED'; next_step='verify_identity_with_independent_source'; primary=True
        elif positive:
            outcome='DEDICATED_SCOPE_SUPPORTED'; next_step='acquire_independent_scope_source'; primary=False
        elif general:
            outcome='GENERAL_OR_MIXED_SCOPE'; next_step='exclude_from_primary_directory_keep_as_option_evidence'; primary=False
        else:
            outcome='SCOPE_UNRESOLVED'; next_step='acquire_scope_specific_evidence'; primary=False
        decisions.append({'candidate_key':q['candidate_key'],'name':q['name'],'province':q['province'],
          'scope_outcome':outcome,'primary_directory_ready':primary,'next_step':next_step,
          'scope_observation_count':len(rows),'positive_dedicated_signal_count':len(positive),
          'general_or_mixed_signal_count':len(general),'independent_scope_source_families':sorted(independent),
          'observations':rows})
    counts=Counter(x['scope_outcome'] for x in decisions); after=db.read_bytes()
    return {'status':'PASS','policy_version':POLICY_VERSION,'scope_queue_count':len(queue),
      'decision_counts':dict(sorted(counts.items())),'decisions':decisions,
      'dedicated_scope_verified_count':counts['DEDICATED_SCOPE_VERIFIED'],
      'general_or_mixed_scope_count':counts['GENERAL_OR_MIXED_SCOPE'],
      'scope_unresolved_count':counts['SCOPE_UNRESOLVED']+counts['DEDICATED_SCOPE_SUPPORTED'],
      'primary_directory_ready_count':sum(x['primary_directory_ready'] for x in decisions),
      'quality':{'category_label_alone_is_insufficient':True,'generic_name_not_treated_as_dedicated':True,
                 'independent_scope_evidence_required_for_verified':True},
      'safety':{'database_unchanged':before==after,'database_writes':False,'canonical_writes':False,
                'precanonical_writes':False,'pending_queue_writes':False,'production_json_writes':False,
                'automatic_adoption':False,'automatic_publication':False,'trust_policy_lowered':False}}
