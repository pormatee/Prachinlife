from __future__ import annotations
import hashlib, math, re, sqlite3
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

POLICY_VERSION="4.2-new-place-discovery-v1"
_NAME_RE=re.compile(r"[^0-9a-zก-๙]+",re.I)
VEG_VALUES={"yes","only"}
VEG_NAME_TERMS=("อาหารเจ","ครัวเจ","ร้านเจ","มังสวิรัติ","vegetarian","vegan")

def _sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def _name(v):
    return _NAME_RE.sub("",(v or "").casefold())

def _distance(a,b,c,d):
    r=6371008.8;p1=math.radians(a);p2=math.radians(c)
    dp=math.radians(c-a);dl=math.radians(d-b)
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return r*2*math.atan2(math.sqrt(h),math.sqrt(1-h))

def build_osm_vegetarian_query(iso3166_2="TH-25"):
    iso=iso3166_2.strip()
    if not iso: raise ValueError("iso3166_2 is required")
    return """[out:json][timeout:120];
area["boundary"="administrative"]["ISO3166-2"="%s"]->.searchArea;
(
 nwr["diet:vegetarian"~"^(yes|only)$",i](area.searchArea);
 nwr["diet:vegan"~"^(yes|only)$",i](area.searchArea);
 nwr["name"~"อาหารเจ|ครัวเจ|ร้านเจ|มังสวิรัติ|vegetarian|vegan",i](area.searchArea);
 nwr["name:th"~"อาหารเจ|ครัวเจ|ร้านเจ|มังสวิรัติ",i](area.searchArea);
);
out center tags;""" % iso

def _candidate(element,province):
    tags=element.get("tags")
    if not isinstance(tags,dict): return None
    name=str(tags.get("name") or tags.get("name:th") or tags.get("name:en") or "").strip()
    if not name:return None
    lat=element.get("lat");lon=element.get("lon")
    if lat is None or lon is None:
        ctr=element.get("center") or {};lat=ctr.get("lat");lon=ctr.get("lon")
    if lat is None or lon is None:return None
    dv=str(tags.get("diet:vegetarian") or "").casefold()
    dvg=str(tags.get("diet:vegan") or "").casefold()
    nk=any(x in name.casefold() for x in VEG_NAME_TERMS)
    if dv not in VEG_VALUES and dvg not in VEG_VALUES and not nk:return None
    rid="osm-%s-%s"%(element.get("type"),element.get("id"))
    reasons=[]
    if dv in VEG_VALUES:reasons.append("diet:vegetarian="+dv)
    if dvg in VEG_VALUES:reasons.append("diet:vegan="+dvg)
    if nk:reasons.append("vegetarian_name_keyword")
    return {"source_type":"osm","source_name":"OpenStreetMap","source_record_id":rid,
      "source_url":"https://www.openstreetmap.org/%s/%s"%(element.get("type"),element.get("id")),
      "name":name,"province":province,"latitude":float(lat),"longitude":float(lon),
      "phone":tags.get("phone") or tags.get("contact:phone"),
      "website":tags.get("website") or tags.get("contact:website"),
      "discovery_reasons":reasons,"raw_tags":tags}


def _normalized_observation(record, province):
    name=str(record.get("name") or "").strip()
    if not name or record.get("latitude") is None or record.get("longitude") is None:
        return None
    reasons=list(record.get("discovery_reasons") or [])
    if not reasons:return None
    return {
      "source_type":str(record.get("source_type") or "web"),
      "source_name":str(record.get("source_name") or "Web"),
      "source_record_id":str(record.get("source_record_id") or ""),
      "source_url":record.get("source_url"),
      "name":name,"province":str(record.get("province") or province),
      "latitude":float(record["latitude"]),"longitude":float(record["longitude"]),
      "phone":record.get("phone"),"website":record.get("website"),
      "discovery_reasons":reasons,"raw_tags":dict(record.get("raw_attributes") or {})}

def discover_new_vegetarian_candidates(database_path,elements,province="ปราจีนบุรี",duplicate_distance_m=150.0):
    db=Path(database_path);before=_sha(db)
    con=sqlite3.connect("%s?mode=ro"%db.resolve().as_uri(),uri=True);con.row_factory=sqlite3.Row
    try: existing=list(con.execute("select place_id,canonical_name,province,latitude,longitude,phone,website from places"))
    finally: con.close()
    found=[];blocked=[];review=[];seen=set()
    for e in elements:
        c=_candidate(e,province) if isinstance(e,dict) and "type" in e and "id" in e else _normalized_observation(e,province)
        if not c or c["source_record_id"] in seen:continue
        seen.add(c["source_record_id"]);best=None
        for x in existing:
            if (x["province"] or "") != province:continue
            dist=None
            if x["latitude"] is not None and x["longitude"] is not None:
                dist=_distance(c["latitude"],c["longitude"],x["latitude"],x["longitude"])
            cn=_name(c["name"]); xn=_name(x["canonical_name"])
            same=bool(cn and xn and cn==xn)
            similarity=SequenceMatcher(None,cn,xn).ratio() if cn and xn else 0.0
            plausible_name=similarity>=0.72
            if same or (plausible_name and dist is not None and dist<=duplicate_distance_m):
                score=(100 if same else int(similarity*40))+(50 if dist is not None and dist<=duplicate_distance_m else 0)
                if best is None or score>best[0]:best=(score,x,dist,same)
        if best:
            _,x,dist,same=best
            item=dict(c,matched_place_id=x["place_id"],matched_name=x["canonical_name"],
                      distance_m=None if dist is None else round(dist,1))
            if same or (dist is not None and dist<=50):
                item["resolution"]="existing_place";blocked.append(item)
            else:
                item["resolution"]="review_possible_duplicate";review.append(item)
        else:
            c["resolution"]="new_place_candidate";found.append(c)
    after=_sha(db)
    return {"status":"PASS","policy_version":POLICY_VERSION,"province":province,"category":"vegetarian",
      "source_observation_count":len(seen),"new_place_candidate_count":len(found),
      "existing_place_match_count":len(blocked),"review_count":len(review),
      "new_place_candidates":found,"existing_place_matches":blocked,"review_candidates":review,
      "candidate_only":True,
      "safety":{"database_unchanged":before==after,"database_writes":False,"evidence_writes":False,
                "canonical_writes":False,"production_json_writes":False,"automatic_adoption":False,
                "trust_policy_lowered":False,"province_agnostic":True}}
