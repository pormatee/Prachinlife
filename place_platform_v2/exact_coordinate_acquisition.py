from __future__ import annotations
import json,math,re,sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION="4.12-exact-coordinate-acquisition-v1"
MAX_SOURCE_DISAGREEMENT_M=120.0

def _load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def _norm(v): return re.sub(r"[^0-9a-zก-๙]+","",str(v or "").casefold(),flags=re.I)
def _dist(a,b,c,d):
    r=6371008.8;p1=math.radians(a);p2=math.radians(c)
    dp=math.radians(c-a);dl=math.radians(d-b)
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return r*2*math.atan2(math.sqrt(h),math.sqrt(1-h))
def _valid_th(lat,lon):
    return 5.0<=lat<=21.0 and 97.0<=lon<=106.5

def acquire_exact_coordinates(*,database_path,geolocation_report_path,observations_path)->dict[str,Any]:
    db=Path(database_path); before=db.read_bytes()
    prior=_load(geolocation_report_path); obs=_load(observations_path)
    results=[]
    for p in prior.get("results",[]):
        name=p["name"];province=p["province"]
        rows=[o for o in obs if _norm(o.get("candidate_name"))==_norm(name)
              and str(o.get("province") or "").strip()==province]
        accepted=[];excluded=[]
        for o in rows:
            if str(o.get("coordinate_owner") or "").strip().casefold()!="candidate":
                excluded.append({**o,"exclusion_reason":"coordinate_not_owned_by_candidate"});continue
            if o.get("latitude") is None or o.get("longitude") is None:
                excluded.append({**o,"exclusion_reason":"coordinates_not_exposed"});continue
            try: lat=float(o["latitude"]);lon=float(o["longitude"])
            except Exception:
                excluded.append({**o,"exclusion_reason":"invalid_coordinate_format"});continue
            if not _valid_th(lat,lon):
                excluded.append({**o,"exclusion_reason":"coordinate_outside_thailand_bounds"});continue
            accepted.append({**o,"latitude":lat,"longitude":lon})

        families=sorted({str(x.get("source_family") or "").strip().casefold() for x in accepted if x.get("source_family")})
        disagreement=False
        max_disagreement=0.0
        for i in range(len(accepted)):
            for j in range(i+1,len(accepted)):
                d=_dist(accepted[i]["latitude"],accepted[i]["longitude"],accepted[j]["latitude"],accepted[j]["longitude"])
                max_disagreement=max(max_disagreement,d)
                if d>MAX_SOURCE_DISAGREEMENT_M: disagreement=True

        if accepted and not disagreement:
            lat=sum(x["latitude"] for x in accepted)/len(accepted)
            lon=sum(x["longitude"] for x in accepted)/len(accepted)
            outcome="EXACT_COORDINATES_VERIFIED"
            next_step="controlled_new_place_adoption_review"
        elif disagreement:
            lat=lon=None
            outcome="COORDINATE_CONFLICT_REVIEW_REQUIRED"
            next_step="resolve_exact_coordinate_conflict"
        else:
            lat=lon=None
            outcome="EXACT_COORDINATES_UNRESOLVED"
            next_step="direct_map_or_operator_coordinate_confirmation"

        results.append({
          "candidate_key":p["candidate_key"],"name":name,"province":province,
          "coordinate_outcome":outcome,
          "accepted_candidate_coordinate_count":len(accepted),
          "independent_coordinate_source_family_count":len(families),
          "accepted_source_families":families,
          "excluded_observations":excluded,
          "max_source_disagreement_m":round(max_disagreement,1),
          "latitude":lat,"longitude":lon,
          "canonical_adoption_ready":outcome=="EXACT_COORDINATES_VERIFIED",
          "next_step":next_step
        })
    after=db.read_bytes()
    counts=Counter(x["coordinate_outcome"] for x in results)
    return {
      "status":"PASS","policy_version":POLICY_VERSION,
      "candidate_count":len(results),"decision_counts":dict(sorted(counts.items())),
      "exact_verified_count":counts["EXACT_COORDINATES_VERIFIED"],
      "unresolved_count":counts["EXACT_COORDINATES_UNRESOLVED"],
      "conflict_count":counts["COORDINATE_CONFLICT_REVIEW_REQUIRED"],
      "results":results,
      "safety":{"database_unchanged":before==after,"database_writes":False,
                "canonical_writes":False,"precanonical_writes":False,
                "production_json_writes":False,"automatic_coordinate_guessing":False,
                "landmark_coordinates_rejected":True,"automatic_adoption":False,
                "trust_policy_lowered":False}
    }
