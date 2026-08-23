from __future__ import annotations
import json, re, sqlite3
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

TRUSTED = {'supported','verified'}
DETAIL_FIELDS = ('address','area','district','subdistrict','opening_hours','phone','website','description','real_image')

@dataclass(frozen=True)
class DetailClaim:
    place_id: str; field_name: str; value: str; source_name: str; source_url: str; source_record_id: str; observed_at: str; metadata: dict

def _osm_ref(text):
    s=str(text or '')
    m=re.search(r'osm-(node|way|relation)-(\d+)',s) or re.search(r'openstreetmap\.org/(node|way|relation)/(\d+)',s)
    return (m.group(1),m.group(2)) if m else None

def _text(v):
    return str(v).strip() if v not in (None,'') else ''

def _address(tags):
    vals=[]
    for k in ('addr:housenumber','addr:street','addr:place','addr:subdistrict','addr:district','addr:province','addr:postcode'):
        v=_text(tags.get(k))
        if v and v not in vals: vals.append(v)
    return ', '.join(vals)

def _httpish(v):
    s=_text(v)
    if not s: return ''
    if s.startswith(('http://','https://')): return s
    if re.match(r'^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/|$)',s): return 'https://'+s
    return ''

def _fields(tags):
    out={}
    mapping={
      'district':('addr:district',),'subdistrict':('addr:subdistrict',),'area':('addr:place','addr:hamlet'),
      'opening_hours':('opening_hours',),'phone':('phone','contact:phone'),'description':('description',)
    }
    for field,keys in mapping.items():
        for k in keys:
            v=_text(tags.get(k))
            if v: out[field]=v; break
    a=_address(tags)
    if a: out['address']=a
    for k in ('website','contact:website'):
        v=_httpish(tags.get(k))
        if v: out['website']=v; break
    for k in ('image',):
        v=_httpish(tags.get(k))
        if v: out['real_image']=v; break
    return out

def collect_claims(database_path, export_path, osm_report_path):
    payload=json.loads(Path(export_path).read_text(encoding='utf-8'))
    raw=json.loads(Path(osm_report_path).read_text(encoding='utf-8'))
    idx={(str(e.get('type')),str(e.get('id'))):e for e in raw.get('elements',[]) if isinstance(e,dict)}
    con=sqlite3.connect(database_path); con.row_factory=sqlite3.Row
    claims=[]; matched=0
    try:
      for p in payload.get('places',[]):
        pid=p['id']; anchor=None
        rows=con.execute("SELECT source_record_id,source_url,status FROM place_evidence WHERE place_id=? ORDER BY observed_at DESC,evidence_id",(pid,)).fetchall()
        for r in rows:
          if str(r['status']).casefold() not in TRUSTED: continue
          ref=_osm_ref(r['source_record_id']) or _osm_ref(r['source_url'])
          if ref and ref in idx: anchor=ref; break
        if not anchor: continue
        matched += 1
        element=idx[anchor]; tags=element.get('tags') or {}
        for field,value in _fields(tags).items():
          url=f"https://www.openstreetmap.org/{anchor[0]}/{anchor[1]}"
          claims.append(DetailClaim(pid,field,value,'OpenStreetMap current observation',url,f'osm-{anchor[0]}-{anchor[1]}',raw.get('fetched_at') or '',{
            'policy_version':'phase11-detail-enrichment-v1','provenance_origin':'direct_osm_snapshot','osm_element_type':anchor[0],'osm_element_id':anchor[1],'source_report':str(Path(osm_report_path).as_posix()),'source_coverage_complete':bool(raw.get('coverage_complete'))
          }))
    finally: con.close()
    return claims, {'published_places':len(payload.get('places',[])),'matched_osm_identity':matched,'raw_coverage_complete':bool(raw.get('coverage_complete'))}

def persist_claims(database_path, claims):
    con=sqlite3.connect(database_path)
    inserted=0
    try:
      before=con.execute('SELECT COUNT(*) FROM places').fetchone()[0]
      for c in claims:
        evid=str(uuid5(NAMESPACE_URL, f"phase11|{c.place_id}|{c.field_name}|{c.source_record_id}|{c.value}"))
        cur=con.execute("INSERT OR IGNORE INTO place_evidence (evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (evid,c.place_id,'osm',c.source_name,c.source_record_id,c.source_url,c.observed_at,'address' if c.field_name in {'address','area','district','subdistrict'} else 'contact' if c.field_name in {'phone','website'} else 'opening_status' if c.field_name=='opening_hours' else 'other',c.field_name,json.dumps(c.value,ensure_ascii=False),'supported',c.observed_at,json.dumps(c.metadata,ensure_ascii=False,sort_keys=True)))
        inserted += cur.rowcount
      after=con.execute('SELECT COUNT(*) FROM places').fetchone()[0]
      if before != after: raise RuntimeError('canonical places changed')
      con.commit()
      return inserted
    finally: con.close()
