from __future__ import annotations
import hashlib, json, re, time
from pathlib import Path
from typing import Any, Callable

from place_platform_v2.osm_live import fetch_overpass
from place_platform_v2.vegetarian_nationwide_coverage import PROVINCES, QUERY_PATTERNS, classify_candidate

POLICY_VERSION = '8-final-vegetarian-real-discovery-v1'


def build_province_osm_query(province: str) -> str:
    p = str(province or '').strip().replace('"', '\\"')
    if not p: raise ValueError('province is required')
    return f'''[out:json][timeout:120];
area["boundary"="administrative"]["admin_level"="4"]["name"="{p}"]->.a;
(
 nwr["amenity"~"^(restaurant|cafe|fast_food|food_court)$"]["diet:vegetarian"~"^(yes|only)$",i](area.a);
 nwr["amenity"~"^(restaurant|cafe|fast_food|food_court)$"]["diet:vegan"~"^(yes|only)$",i](area.a);
 nwr["name"~"อาหารเจ|ครัวเจ|ร้านเจ|มังสวิรัติ|vegetarian|vegan",i](area.a);
 nwr["name:th"~"อาหารเจ|ครัวเจ|ร้านเจ|มังสวิรัติ",i](area.a);
);
out center tags;'''


def _coords(e):
    lat=e.get('lat'); lon=e.get('lon')
    if lat is None or lon is None:
        c=e.get('center') or {}; lat=c.get('lat'); lon=c.get('lon')
    return lat,lon


def normalize_osm_element(e: dict[str,Any], province: str) -> dict[str,Any] | None:
    tags=e.get('tags') or {}
    name=str(tags.get('name') or tags.get('name:th') or tags.get('name:en') or '').strip()
    lat,lon=_coords(e)
    if not name or lat is None or lon is None:return None
    scope=classify_candidate(name,tags)
    if scope['scope']=='UNRESOLVED':return None
    typ=str(e.get('type') or ''); oid=e.get('id')
    if not typ or oid is None:return None
    return {
      'observation_id':f'osm-{typ}-{oid}','source_type':'osm','source_name':'OpenStreetMap',
      'source_family':'openstreetmap','source_record_id':f'osm-{typ}-{oid}',
      'source_url':f'https://www.openstreetmap.org/{typ}/{oid}','name':name,'province':province,
      'latitude':float(lat),'longitude':float(lon),'phone':tags.get('phone') or tags.get('contact:phone'),
      'website':tags.get('website') or tags.get('contact:website'),'category':'vegetarian',
      'directory_scope':scope['scope'],'primary_candidate':scope['primary_candidate'],
      'scope_reason':scope['reason'],'raw_attributes':tags}


def dedupe_observations(rows):
    out={}
    for r in rows:
        if not isinstance(r,dict):continue
        key=str(r.get('observation_id') or r.get('source_record_id') or '').strip()
        if key:out[key]=r
    return [out[k] for k in sorted(out)]


def load_json(path,default):
    p=Path(path)
    if not p.exists():return default
    return json.loads(p.read_text(encoding='utf-8'))


def save_json(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def run_osm_discovery(*, ledger_path, observations_path, provinces=None, fetcher:Callable[[str],Any]=None,
                      max_provinces=None, retry_failed=False, sleep_seconds=0.0):
    provinces=list(provinces or PROVINCES)
    ledger=load_json(ledger_path,{'policy_version':POLICY_VERSION,'provinces':{}})
    state=ledger.setdefault('provinces',{})
    existing=load_json(observations_path,[]); existing=existing if isinstance(existing,list) else []
    fetcher=fetcher or (lambda q: fetch_overpass(q))
    attempted=completed=failed=0; new_rows=[]
    for province in provinces:
        prev=state.get(province,{})
        if prev.get('status')=='completed':continue
        if prev.get('status')=='failed' and not retry_failed:continue
        if max_provinces is not None and attempted>=max_provinces:break
        attempted+=1
        try:
            report=fetcher(build_province_osm_query(province))
            elements=list(report.elements if hasattr(report,'elements') else report.get('elements',[]))
            rows=[x for x in (normalize_osm_element(e,province) for e in elements) if x]
            new_rows.extend(rows);completed+=1
            state[province]={'status':'completed','observation_count':len(rows),'endpoint':getattr(report,'endpoint',None),
                             'attempts':getattr(report,'attempts',1),'updated_at':int(time.time())}
        except Exception as exc:
            failed+=1
            state[province]={'status':'failed','error':f'{type(exc).__name__}: {exc}'[:500],'updated_at':int(time.time())}
        save_json(ledger_path,ledger)
        save_json(observations_path,dedupe_observations(existing+new_rows))
        if sleep_seconds:time.sleep(sleep_seconds)
    all_rows=dedupe_observations(existing+new_rows)
    primary=sum(bool(x.get('primary_candidate')) for x in all_rows)
    options=sum(x.get('directory_scope')=='OPTION_AVAILABLE' for x in all_rows)
    counts={s:sum(1 for x in state.values() if x.get('status')==s) for s in ('completed','failed')}
    counts['pending']=len(PROVINCES)-counts['completed']-counts['failed']
    return {'status':'PASS','policy_version':POLICY_VERSION,'attempted_this_run':attempted,
            'completed_this_run':completed,'failed_this_run':failed,'province_status':counts,
            'unique_observations':len(all_rows),'primary_observations':primary,'option_observations':options,
            'real_world_completeness_claimed':False,'automatic_adoption':False,'production_writes':False}


def build_web_job_export():
    return [{'province':p,'query':q.format(province=p),'category':'vegetarian','requested_scopes':['DEDICATED_OR_NAMED','OPTION_AVAILABLE']}
            for p in PROVINCES for q in QUERY_PATTERNS]
