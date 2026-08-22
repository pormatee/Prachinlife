from __future__ import annotations
import json,re,sqlite3,urllib.request
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from pathlib import Path
from .publication_export import _load_places_and_evidence
from .publication_confidence import CORE_FIELDS,_matching,_lineages,_has_conflict

POLICY_VERSION='staged-milestone-v1'
OSM_RE=re.compile(r'osm-(node|way|relation)-(\d+)')
NEGATIVE_KEYS={'disused','abandoned','demolished','razed'}
NEGATIVE_VALUES={'closed','inactive','disused','abandoned','demolished','razed'}

def osm_ref(evidence):
    for e in evidence:
        m=OSM_RE.search(e.source.source_record_id or '')
        if m:return m.group(1),m.group(2)
    return None

def select_pilot_queue(database_path,province='ปราจีนบุรี',limit=20):
    places,by=_load_places_and_evidence(database_path,province)
    name_counts={}
    for p in places:name_counts[p.canonical_name.strip().casefold()]=name_counts.get(p.canonical_name.strip().casefold(),0)+1
    out=[]
    for p in places:
        ev=by.get(p.identity.place_id,())
        ref=osm_ref(ev)
        if not ref or ref[0]!='node':continue
        if name_counts[p.canonical_name.strip().casefold()]!=1:continue
        ok=True
        for f in CORE_FIELDS:
            v=getattr(p,f)
            if not _lineages(_matching(ev,f,v)) or _has_conflict(ev,f,v):ok=False;break
        if not ok:continue
        out.append({'place_id':p.identity.place_id,'canonical_name':p.canonical_name,'province':p.province,'latitude':p.location.latitude if p.location else None,'longitude':p.location.longitude if p.location else None,'osm_type':ref[0],'osm_id':ref[1]})
    return out[:limit]

def parse_osm_node(payload:bytes):
    import xml.etree.ElementTree as ET
    root=ET.fromstring(payload); node=root.find('node')
    if node is None: raise ValueError('OSM response has no node')
    tags={t.attrib['k']:t.attrib.get('v','') for t in node.findall('tag')}
    return {'lat':float(node.attrib['lat']),'lon':float(node.attrib['lon']),'tags':tags,'visible':node.attrib.get('visible','true')!='false'}

def observation_status(obs, expected_lat, expected_lon):
    if not obs['visible']:return 'negative','OSM object is not visible'
    tags={str(k).casefold():str(v).casefold() for k,v in obs['tags'].items()}
    if any(k in tags for k in NEGATIVE_KEYS) or any(v in NEGATIVE_VALUES for v in tags.values()):return 'negative','OSM object carries closure/disused marker'
    if abs(obs['lat']-expected_lat)>0.002 or abs(obs['lon']-expected_lon)>0.002:return 'conflict','OSM object moved materially from canonical location'
    return 'current_listing','current OSM object remains present without closure marker'

def acquire_osm_queue(queue,fetcher=None,observed_at=None):
    fetcher=fetcher or (lambda url: urllib.request.urlopen(url,timeout=20).read())
    when=observed_at or datetime.now(timezone.utc)
    results=[]
    for item in queue:
        url=f"https://api.openstreetmap.org/api/0.6/node/{item['osm_id']}"
        try:
            obs=parse_osm_node(fetcher(url)); status,reason=observation_status(obs,item['latitude'],item['longitude'])
            results.append({**item,'status':status,'reason':reason,'source_name':'OpenStreetMap current observation','source_url':f"https://www.openstreetmap.org/node/{item['osm_id']}",'observed_at':when.isoformat(),'observed_latitude':obs['lat'],'observed_longitude':obs['lon']})
        except Exception as exc:
            results.append({**item,'status':'acquisition_error','reason':str(exc),'observed_at':when.isoformat()})
    return results

def staged_eligible(place,evidence,now=None,max_age_days=30):
    reasons=[]
    for f in CORE_FIELDS:
        v=getattr(place,f)
        if not _lineages(_matching(evidence,f,v)):reasons.append(f'{f} unsupported')
        elif _has_conflict(evidence,f,v):reasons.append(f'{f} conflict')
    now=now or datetime.now(timezone.utc); cutoff=now-timedelta(days=max_age_days)
    current=[]; negative=[]
    for e in evidence:
        md=dict(e.metadata or {})
        if md.get('provenance_origin')!='current_existence_observation':continue
        if e.observed_at<cutoff:continue
        if e.field_name=='existence' and e.value is True:current.append(e)
        if e.field_name in {'existence','lifecycle'} and e.value in {False,'closed','inactive'}:negative.append(e)
    if negative:reasons.append('recent negative existence/lifecycle evidence')
    if not current:reasons.append('no recent explicit existence observation')
    return not reasons,tuple(reasons)

def _ensure_observation_table(con):
    con.execute('''CREATE TABLE IF NOT EXISTS staged_existence_observations(
      observation_id TEXT PRIMARY KEY, place_id TEXT NOT NULL REFERENCES places(place_id),
      source_url TEXT NOT NULL, status TEXT NOT NULL, observed_at TEXT NOT NULL,
      evidence_id TEXT, policy_version TEXT NOT NULL, payload_json TEXT NOT NULL)''')

def commit_current_observations(database_path, observations):
    import uuid
    from .sqlite_store import _dump
    con=sqlite3.connect(database_path)
    committed=[]
    try:
      with con:
        _ensure_observation_table(con)
        for o in observations:
          if o.get('status')!='current_listing':continue
          oid=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{o['place_id']}|{o['source_url']}|{o['observed_at']}"))
          if con.execute('select 1 from staged_existence_observations where observation_id=?',(oid,)).fetchone():continue
          eid=str(uuid.uuid5(uuid.NAMESPACE_URL,oid+'|existence'))
          md={'provenance_origin':'current_existence_observation','policy_version':POLICY_VERSION,'observation_status':'current_listing'}
          con.execute('''insert into place_evidence(evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json)
          values(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(eid,o['place_id'],'osm','OpenStreetMap current observation',f"osm-node-{o['osm_id']}",o['source_url'],o['observed_at'],'existence','existence','true','supported',o['observed_at'],json.dumps(md,ensure_ascii=False,sort_keys=True)))
          con.execute('insert into staged_existence_observations values(?,?,?,?,?,?,?,?)',(oid,o['place_id'],o['source_url'],o['status'],o['observed_at'],eid,POLICY_VERSION,json.dumps(o,ensure_ascii=False,sort_keys=True)))
          committed.append({'observation_id':oid,'place_id':o['place_id'],'evidence_id':eid})
      return committed
    finally:con.close()

def eligible_place_ids(database_path,province='ปราจีนบุรี'):
    places,by=_load_places_and_evidence(database_path,province);out=[];blocked=[]
    for p in places:
      ok,reasons=staged_eligible(p,by.get(p.identity.place_id,()))
      (out if ok else blocked).append(p.identity.place_id if ok else {'place_id':p.identity.place_id,'reasons':reasons})
    return out,blocked

def build_compat_staging(database_path,repo_root,output_root,province='ปราจีนบุรี'):
    eligible,_=eligible_place_ids(database_path,province); eligible=set(eligible)
    con=sqlite3.connect(database_path);con.row_factory=sqlite3.Row
    try:
      mapping={}
      for pid in eligible:
        rows=con.execute('select source_record_id from place_evidence where place_id=?',(pid,)).fetchall()
        for r in rows:
          rec=r['source_record_id'] or ''
          if '#' in rec:
            fn,rid=rec.split('#',1)
            if fn in {'prachinlife_index.json','vegetarian_index.json','go_index.json','service_index.json'}:mapping.setdefault(fn,set()).add(rid)
    finally:con.close()
    root=Path(repo_root);outroot=Path(output_root);outroot.mkdir(parents=True,exist_ok=True);counts={}
    for fn in ('prachinlife_index.json','vegetarian_index.json','go_index.json','service_index.json'):
      src=json.loads((root/fn).read_text(encoding='utf-8')); ids=mapping.get(fn,set())
      if fn=='prachinlife_index.json':
        payload=[x for x in src if x.get('content_type')=='deal' or x.get('id') in ids]
      else:payload=[x for x in src if x.get('id') in ids]
      (outroot/fn).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');counts[fn]=len(payload)
    manifest={'policy_version':POLICY_VERSION,'province':province,'eligible_place_count':len(eligible),'files':counts,'production_unchanged':True}
    (outroot/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
