from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from urllib.parse import urlparse

POLICY_VERSION='8-final-vegetarian-web-pilot-v1'
PILOT_PROVINCES=('กรุงเทพมหานคร','ชลบุรี','ฉะเชิงเทรา')
PRIMARY_TERMS=('อาหารเจ','ร้านเจ','เจ ','มังสวิรัติ','vegetarian','vegan')
OPTION_TERMS=('มีเมนูเจ','เมนูเจ','มีอาหารเจ','veg option','vegetarian option','vegan option')

def _norm(s): return re.sub(r'\s+',' ',str(s or '').strip()).casefold()
def source_family(url):
    h=(urlparse(str(url or '')).hostname or '').lower().removeprefix('www.')
    return h or 'unknown-web'
def classify_web_observation(row):
    name=_norm(row.get('name')); text=_norm(' '.join(str(row.get(k) or '') for k in ('name','category_text','evidence_text','description')))
    if any(t.casefold() in name for t in PRIMARY_TERMS) or row.get('dedicated') is True:
        return {'directory_scope':'DEDICATED_OR_NAMED','primary_candidate':True,'scope_reason':'dedicated_or_named_web_evidence'}
    if row.get('option_available') is True or (row.get('option_explicit') is True and any(t.casefold() in text for t in OPTION_TERMS)):
        return {'directory_scope':'OPTION_AVAILABLE','primary_candidate':False,'scope_reason':'explicit_option_web_evidence'}
    if ('อาหารเจ' in text or 'มังสวิรัติ' in text or 'vegetarian' in text or 'vegan' in text) and row.get('category_explicit') is True:
        return {'directory_scope':'DEDICATED_OR_NAMED','primary_candidate':True,'scope_reason':'explicit_vegetarian_category'}
    return {'directory_scope':'UNRESOLVED','primary_candidate':False,'scope_reason':'insufficient_web_scope_evidence'}

def normalize_web_observation(row):
    if not isinstance(row,dict): return None
    name=str(row.get('name') or '').strip(); province=str(row.get('province') or '').strip(); url=str(row.get('source_url') or '').strip()
    if not name or province not in PILOT_PROVINCES or not url:return None
    scope=classify_web_observation(row)
    if scope['directory_scope']=='UNRESOLVED':return None
    rid=str(row.get('source_record_id') or hashlib.sha1((url+'|'+name).encode()).hexdigest()[:20])
    return {'observation_id':'web-'+hashlib.sha1((source_family(url)+'|'+rid).encode()).hexdigest()[:20],
      'source_type':'web','source_name':str(row.get('source_name') or source_family(url)),
      'source_family':source_family(url),'source_record_id':rid,'source_url':url,'name':name,'province':province,
      'address':row.get('address'),'phone':row.get('phone'),'latitude':row.get('latitude'),'longitude':row.get('longitude'),
      'category':'vegetarian',**scope,'evidence_text':row.get('evidence_text') or row.get('category_text')}

def _name_key(s):
    return re.sub(r'[^0-9a-zก-๙]+','',_norm(s))
def dedupe_web_observations(rows):
    out={}
    for raw in rows:
        r=normalize_web_observation(raw) if 'directory_scope' not in raw else raw
        if not r:continue
        key=(r['province'],_name_key(r['name']))
        old=out.get(key)
        if old is None or (not old.get('phone') and r.get('phone')):out[key]=r
    return list(out.values())
def existing_names(index_rows):
    return {(str(r.get('location',{}).get('province') or r.get('province') or ''),_name_key(r.get('title') or r.get('name'))) for r in index_rows if isinstance(r,dict)}
def build_pilot_report(rows,index_rows):
    obs=dedupe_web_observations(rows); existing=existing_names(index_rows); by={}
    for p in PILOT_PROVINCES:
        rr=[r for r in obs if r['province']==p]; primary=[r for r in rr if r['primary_candidate']]; options=[r for r in rr if r['directory_scope']=='OPTION_AVAILABLE']
        net=[r for r in rr if (p,_name_key(r['name'])) not in existing]
        by[p]={'unique':len(rr),'primary':len(primary),'option_available':len(options),'net_new':len(net)}
    total=sum(x['unique'] for x in by.values())
    status='PASS' if total>0 and all(by[p]['unique']>0 for p in PILOT_PROVINCES) else 'FAIL'
    return {'status':status,'policy_version':POLICY_VERSION,'provinces':list(PILOT_PROVINCES),'by_province':by,
      'unique_observations':total,'primary_observations':sum(x['primary'] for x in by.values()),
      'option_observations':sum(x['option_available'] for x in by.values()),'net_new_candidates':sum(x['net_new'] for x in by.values()),
      'zero_result_gate':True,'automatic_adoption':False,'production_writes':False,'trust_policy_lowered':False,
      'real_world_completeness_claimed':False}
def load(path,default):
    p=Path(path);return json.loads(p.read_text(encoding='utf8')) if p.exists() else default
def save(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
