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

def parse_osm_object(payload:bytes, osm_type):
    import xml.etree.ElementTree as ET
    root=ET.fromstring(payload)
    obj=root.find(osm_type)
    if obj is None:
        raise ValueError(f'OSM response has no {osm_type}')
    tags={t.attrib['k']:t.attrib.get('v','') for t in obj.findall('tag')}
    if osm_type == 'node':
        lat=float(obj.attrib['lat'])
        lon=float(obj.attrib['lon'])
    else:
        center=root.find('way/center')
        lat=float(center.attrib['lat']) if center is not None else None
        lon=float(center.attrib['lon']) if center is not None else None
    return {'lat':lat,'lon':lon,'tags':tags,'visible':obj.attrib.get('visible','true')!='false'}


def parse_osm_node(payload: bytes):
    return parse_osm_object(payload, 'node')


def observation_status(obs, expected_lat, expected_lon):
    if not obs['visible']:return 'negative','OSM object is not visible'
    tags={str(k).casefold():str(v).casefold() for k,v in obs['tags'].items()}
    if any(k in tags for k in NEGATIVE_KEYS) or any(v in NEGATIVE_VALUES for v in tags.values()):return 'negative','OSM object carries closure/disused marker'
    if abs(obs['lat']-expected_lat)>0.002 or abs(obs['lon']-expected_lon)>0.002:return 'conflict','OSM object moved materially from canonical location'
    return 'current_listing','current OSM object remains present without closure marker'


def observation_status_for_item(obs, item):
    # Node: preserve existing location-drift protection.
    if item.get('osm_type') == 'node':
        return observation_status(
            obs,
            item['latitude'],
            item['longitude'],
        )

    # Way: existence is determined by the current OSM object itself.
    # A polygon/building/area must not be rejected by node-style
    # point-distance comparison.
    if not obs['visible']:
        return 'negative', 'OSM object is not visible'

    tags = {
        str(k).casefold(): str(v).casefold()
        for k, v in obs['tags'].items()
    }

    if (
        any(k in tags for k in NEGATIVE_KEYS)
        or any(v in NEGATIVE_VALUES for v in tags.values())
    ):
        return (
            'negative',
            'OSM object carries closure/disused marker',
        )

    return (
        'current_listing',
        'current OSM way remains present without closure marker',
    )


def _osm_api_url(item):
    osm_type = item["osm_type"]
    osm_id = item["osm_id"]
    suffix = "/full" if osm_type == "way" else ""
    return f"https://api.openstreetmap.org/api/0.6/{osm_type}/{osm_id}{suffix}"


def _osm_public_url(item):
    return f"https://www.openstreetmap.org/{item['osm_type']}/{item['osm_id']}"


def acquire_osm_queue(queue, fetcher=None, observed_at=None):
    fetcher = fetcher or (lambda url: urllib.request.urlopen(url, timeout=20).read())
    when = observed_at or datetime.now(timezone.utc)
    results = []
    for item in queue:
        url = _osm_api_url(item)
        try:
            obs = parse_osm_object(fetcher(url), item["osm_type"])
            status, reason = observation_status_for_item(obs, item)
            results.append({
                **item,
                "status": status,
                "reason": reason,
                "source_name": "OpenStreetMap current observation",
                "source_url": _osm_public_url(item),
                "observed_at": when.isoformat(),
                "observed_latitude": obs["lat"],
                "observed_longitude": obs["lon"],
            })
        except Exception as exc:
            results.append({
                **item,
                "status": "acquisition_error",
                "reason": str(exc),
                "observed_at": when.isoformat(),
            })
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
          values(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(eid,o['place_id'],'osm','OpenStreetMap current observation',f"osm-{o.get('osm_type','node')}-{o['osm_id']}",o['source_url'],o['observed_at'],'existence','existence','true','supported',o['observed_at'],json.dumps(md,ensure_ascii=False,sort_keys=True)))
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
def select_observation_queue(
    database_path,
    province='ปราจีนบุรี',
    limit=20,
):
    """
    Select the next deterministic batch of places whose current
    existence can be checked automatically through an OSM node.

    Unlike select_pilot_queue(), this rollout queue excludes places
    that are already staged-eligible.  It deliberately does not
    expand to OSM ways/relations; those require a separate policy.
    """
    if limit < 0:
        raise ValueError('limit must be >= 0')
    if limit == 0:
        return []

    places, by = _load_places_and_evidence(
        database_path,
        province,
    )

    eligible, _ = eligible_place_ids(
        database_path,
        province,
    )
    eligible = set(eligible)

    name_counts = {}
    for place in places:
        key = place.canonical_name.strip().casefold()
        name_counts[key] = name_counts.get(key, 0) + 1

    queue = []

    for place in places:
        place_id = place.identity.place_id

        # Critical rollout-pagination guard:
        # never acquire the already-eligible pilot again.
        if place_id in eligible:
            continue

        evidence = by.get(place_id, ())
        ref = osm_ref(evidence)

        # Keep first rollout generation on the already-proven
        # OSM-node acquisition path only.
        if not ref or ref[0] != 'node':
            continue

        name_key = place.canonical_name.strip().casefold()
        if name_counts[name_key] != 1:
            continue

        core_ok = True

        for field_name in CORE_FIELDS:
            value = getattr(place, field_name)

            if not _lineages(
                _matching(
                    evidence,
                    field_name,
                    value,
                )
            ):
                core_ok = False
                break

            if _has_conflict(
                evidence,
                field_name,
                value,
            ):
                core_ok = False
                break

        if not core_ok:
            continue

        queue.append(
            {
                'place_id': place_id,
                'canonical_name': place.canonical_name,
                'province': place.province,
                'latitude': (
                    place.location.latitude
                    if place.location
                    else None
                ),
                'longitude': (
                    place.location.longitude
                    if place.location
                    else None
                ),
                'osm_type': ref[0],
                'osm_id': ref[1],
            }
        )

    # Explicit ordering makes batch boundaries reproducible even if
    # repository query ordering changes in the future.
    queue.sort(
        key=lambda item: (
            item['place_id'],
            item['canonical_name'].casefold(),
            item['osm_id'],
        )
    )

    return queue[:limit]


def select_identity_anchor_queue(database_path, province='ปราจีนบุรี', limit=None):
    """Select non-eligible places anchored by a unique OSM object and location.

    Duplicate canonical names are allowed because identity is anchored to the
    OSM object reference, not the display name. Core-field evidence must still
    be supported and conflict-free.
    """
    if limit is not None and limit < 0:
        raise ValueError('limit must be >= 0 or None')

    places, by = _load_places_and_evidence(database_path, province)
    eligible, _ = eligible_place_ids(database_path, province)
    eligible = set(eligible)

    ref_counts = {}
    refs_by_place = {}
    for place in places:
        ref = osm_ref(by.get(place.identity.place_id, ()))
        if ref:
            refs_by_place[place.identity.place_id] = ref
            ref_counts[ref] = ref_counts.get(ref, 0) + 1

    out = []
    for place in places:
        pid = place.identity.place_id
        if pid in eligible or place.location is None:
            continue
        ref = refs_by_place.get(pid)
        if not ref or ref_counts.get(ref) != 1:
            continue
        evidence = by.get(pid, ())
        ok = True
        for field_name in CORE_FIELDS:
            value = getattr(place, field_name)
            if not _lineages(_matching(evidence, field_name, value)) or _has_conflict(evidence, field_name, value):
                ok = False
                break
        if not ok:
            continue
        out.append({
            'place_id': pid,
            'canonical_name': place.canonical_name,
            'province': place.province,
            'latitude': place.location.latitude,
            'longitude': place.location.longitude,
            'osm_type': ref[0],
            'osm_id': ref[1],
        })

    out.sort(key=lambda item: (item['place_id'], item['osm_type'], item['osm_id']))
    return out if limit is None else out[:limit]
