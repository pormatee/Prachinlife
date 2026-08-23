from __future__ import annotations
import json, sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

POLICY_VERSION='6-final-prachinburi-data-expansion-quality-v1'
CORE_CATEGORIES=('restaurant','cafe','vegetarian','attraction','temple','nature','park','fuel','pharmacy','clinic','laundry','car_repair')

def _cats(raw):
    try:v=json.loads(raw or '[]')
    except Exception:return []
    if isinstance(v,dict) and v.get('__type__') in {'list','tuple'}:v=v.get('items',[])
    return [str(x) for x in v] if isinstance(v,list) else []

def audit_prachinburi_data_quality(*,database_path:str|Path,province='ปราจีนบุรี',categories=None)->dict[str,Any]:
    categories=tuple(categories or CORE_CATEGORIES)
    con=sqlite3.connect(Path(database_path));con.row_factory=sqlite3.Row
    try:
        rows=[dict(r) for r in con.execute('select place_id,canonical_name,latitude,longitude,address_text,province,categories_json,phone,website,lifecycle from places where province=?',(province,))]
        ev={r['place_id']:r['n'] for r in con.execute('select place_id,count(*) n from place_evidence group by place_id')}
    finally:con.close()
    counts=Counter();quality=defaultdict(lambda:Counter(total=0,coords=0,address=0,phone=0,website=0,lifecycle_known=0,evidence=0))
    for r in rows:
        cats=_cats(r['categories_json'])
        for cat in cats:
            counts[cat]+=1
            if cat not in categories:continue
            q=quality[cat];q['total']+=1
            q['coords']+=int(r['latitude'] is not None and r['longitude'] is not None)
            q['address']+=int(bool(str(r['address_text'] or '').strip()))
            q['phone']+=int(bool(str(r['phone'] or '').strip()))
            q['website']+=int(bool(str(r['website'] or '').strip()))
            q['lifecycle_known']+=int(str(r['lifecycle'] or '').lower() not in {'','unknown'})
            q['evidence']+=int(ev.get(r['place_id'],0)>0)
    by={}
    for cat in categories:
        q=quality[cat];n=q['total'];
        by[cat]={'canonical_count':n,'coordinates_ready':q['coords'],'address_ready':q['address'],'phone_ready':q['phone'],'website_ready':q['website'],'lifecycle_known':q['lifecycle_known'],'has_evidence':q['evidence']}
        by[cat]['quality_gaps']={k:n-v for k,v in [('coordinates',q['coords']),('address',q['address']),('phone',q['phone']),('website',q['website']),('lifecycle',q['lifecycle_known']),('evidence',q['evidence'])]}
    return {'status':'PASS','policy_version':POLICY_VERSION,'scope':{'province':province,'categories':list(categories)},'canonical_place_count':len(rows),'category_counts':dict(sorted(counts.items())),'categories':by,'real_world_completeness_claimed':False}

def build_expansion_work(*,audit:dict[str,Any],existing_cycle:dict[str,Any]|None=None)->list[dict[str,Any]]:
    out=[];province=audit['scope']['province']
    for cat,q in audit['categories'].items():
        n=q['canonical_count']; gaps=q['quality_gaps']
        if n==0:
            queue,action,blockers='coverage_discovery','discover_category_places',['zero_canonical_coverage']
        elif n<3:
            queue,action,blockers='coverage_discovery','expand_category_coverage',['thin_canonical_coverage']
        elif gaps['address']==n or gaps['lifecycle']==n:
            queue,action,blockers='quality_enrichment','enrich_high_value_place_fields',['systematic_quality_gap']
        elif any(gaps[x] for x in ('address','phone','website','lifecycle','evidence')):
            queue,action,blockers='quality_enrichment','enrich_missing_place_fields',['partial_quality_gap']
        else:continue
        out.append({'candidate_id':None,'name':f'{province}:{cat}','queue':queue,'next_action':action,'blockers':blockers,'category_scope':cat,'metrics':q})
    # Preserve concrete Phase-5 work alongside category-level expansion work.
    for x in (existing_cycle or {}).get('work_items',[]):
        y=dict(x);y.setdefault('category_scope',(existing_cycle or {}).get('scope',{}).get('category','vegetarian'));out.append(y)
    return out
