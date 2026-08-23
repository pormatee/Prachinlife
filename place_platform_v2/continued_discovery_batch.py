from __future__ import annotations
import hashlib,json,re,sqlite3
from collections import defaultdict,Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

POLICY_VERSION="4.9-continue-discovery-batch-v1"

def _norm_name(v):
    return re.sub(r"[^0-9a-zก-๙]+","",str(v or "").casefold(),flags=re.I)

def _phones(v):
    raw=str(v or "")
    vals=set()
    for token in re.findall(r"\+?\d[\d\s\-()]{6,}\d",raw):
        d=re.sub(r"\D","",token)
        if d.startswith("66") and len(d)>=10:d="0"+d[2:]
        if 8<=len(d)<=12:vals.add(d)
    return vals

def _candidate_key(name,province):
    return hashlib.sha256((_norm_name(name)+"|"+str(province or "").strip().casefold()).encode()).hexdigest()

def _load(path,default):
    p=Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def continue_discovery_batch(*,database_path,observations_path,prior_discovery_report_path=None)->dict[str,Any]:
    db=Path(database_path)
    before=db.read_bytes()
    observations=_load(observations_path,[])
    if not isinstance(observations,list):raise ValueError("batch observations must be a list")
    prior=_load(prior_discovery_report_path,{}) if prior_discovery_report_path else {}

    con=sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro",uri=True);con.row_factory=sqlite3.Row
    canonical=[dict(r) for r in con.execute("select place_id,canonical_name,province,phone,website,latitude,longitude from places")]
    precanonical=[]
    pending=[]
    try:
        precanonical=[dict(r) for r in con.execute("select candidate_id,candidate_key,proposed_name,province,status from precanonical_candidates")]
    except sqlite3.OperationalError:pass
    try:
        pending=[dict(r) for r in con.execute("""select q.candidate_id,c.proposed_name,c.province,q.reason,q.current_state,q.next_action
          from precanonical_pending_review q join precanonical_candidates c on c.candidate_id=q.candidate_id
          where q.status='pending_manual_confirmation'""")]
    except sqlite3.OperationalError:pass
    con.close()

    prior_candidates=(prior.get("new_place_candidates") or []) if isinstance(prior,dict) else []
    prior_keys={_candidate_key(x.get("name"),x.get("province")) for x in prior_candidates}

    # Group source observations that clearly refer to the same proposed candidate.
    groups={}
    for o in observations:
        if not isinstance(o,dict):continue
        name=str(o.get("name") or "").strip();province=str(o.get("province") or "").strip()
        if not name or not province:continue
        explicit=str(o.get("candidate_group") or "").strip()
        key=explicit or _candidate_key(name,province)
        if key not in groups:
            groups[key]={"candidate_key":_candidate_key(name,province),"name":name,"province":province,
                         "category":str(o.get("category") or "vegetarian"),"observations":[]}
        groups[key]["observations"].append(o)

    results=[]
    for g in groups.values():
        name=g["name"];province=g["province"];nname=_norm_name(name)
        obs=g["observations"]
        pset=set()
        families=set()
        latitudes=[];longitudes=[]
        for o in obs:
            pset |= _phones(o.get("phone"))
            fam=str(o.get("source_family") or o.get("source_name") or "").strip().casefold()
            if fam:families.add(fam)
            if o.get("latitude") is not None and o.get("longitude") is not None:
                latitudes.append(float(o["latitude"]));longitudes.append(float(o["longitude"]))

        canon_matches=[]
        for x in canonical:
            same_province=str(x.get("province") or "").strip()==province
            xphones=_phones(x.get("phone"))
            phone_match=bool(pset & xphones)
            xn=_norm_name(x.get("canonical_name"))
            exact_name=bool(nname and xn and nname==xn)
            sim=SequenceMatcher(None,nname,xn).ratio() if nname and xn else 0.0
            strong_name=same_province and (exact_name or sim>=0.90)
            if phone_match or strong_name:
                canon_matches.append({"place_id":x["place_id"],"canonical_name":x["canonical_name"],
                                      "phone_match":phone_match,"name_similarity":round(sim,3)})
        pending_matches=[x for x in pending if str(x.get("province") or "").strip()==province
                         and _norm_name(x.get("proposed_name"))==nname]
        pre_matches=[x for x in precanonical if str(x.get("province") or "").strip()==province
                     and _norm_name(x.get("proposed_name"))==nname]
        ck=g["candidate_key"]
        is_prior=ck in prior_keys

        if canon_matches:
            state="EXISTING_CANONICAL"
            next_step="attach_as_existing_place_evidence_if_useful"
        elif pending_matches:
            state="PENDING_MANUAL_REVIEW"
            next_step="skip_until_pending_resolution"
        elif pre_matches:
            state="PRECANONICAL_EXISTING"
            next_step="continue_precanonical_workflow"
        elif is_prior:
            state="KNOWN_DISCOVERY_CANDIDATE"
            next_step="continue_identity_evidence_acquisition"
        else:
            state="NEW_DISCOVERY_CANDIDATE"
            next_step="verify_identity_batch"

        results.append({
          "candidate_key":ck,"name":name,"province":province,"category":g["category"],
          "batch_state":state,"next_step":next_step,
          "source_observation_count":len(obs),"independent_source_family_count":len(families),
          "source_families":sorted(families),"phones":sorted(pset),
          "has_coordinates":bool(latitudes),"canonical_matches":canon_matches,
          "pending_matches":pending_matches,"precanonical_matches":pre_matches,
          "observations":obs,
        })

    order={"NEW_DISCOVERY_CANDIDATE":0,"KNOWN_DISCOVERY_CANDIDATE":1,"EXISTING_CANONICAL":2,
           "PENDING_MANUAL_REVIEW":3,"PRECANONICAL_EXISTING":4}
    results.sort(key=lambda x:(order.get(x["batch_state"],99),-x["independent_source_family_count"],x["name"]))
    counts=Counter(x["batch_state"] for x in results)
    new=[x for x in results if x["batch_state"]=="NEW_DISCOVERY_CANDIDATE"]
    verification_queue=[{
       "candidate_key":x["candidate_key"],"name":x["name"],"province":x["province"],"category":x["category"],
       "independent_source_family_count":x["independent_source_family_count"],
       "source_observation_count":x["source_observation_count"],
       "identity_evidence_ready":x["independent_source_family_count"]>=2,
       "needs_second_independent_source":x["independent_source_family_count"]<2,
       "needs_geolocation":not x["has_coordinates"],
       "next_step":"verify_identity_batch" if x["independent_source_family_count"]>=2 else "acquire_second_independent_source",
    } for x in new]

    after=db.read_bytes()
    return {
      "status":"PASS","policy_version":POLICY_VERSION,
      "source_observation_count":sum(x["source_observation_count"] for x in results),
      "candidate_group_count":len(results),"batch_state_counts":dict(sorted(counts.items())),
      "new_candidate_count":len(new),"verification_queue_count":len(verification_queue),
      "batch_results":results,"verification_queue":verification_queue,
      "pending_queue_count":len(pending),
      "discovery_continues":True,
      "safety":{"database_unchanged":before==after,"database_writes":False,"canonical_writes":False,
                "precanonical_writes":False,"pending_queue_writes":False,"production_json_writes":False,
                "automatic_adoption":False,"automatic_publication":False,
                "pending_candidates_do_not_block_discovery":True,"trust_policy_lowered":False,
                "batch_deduplication_enabled":True}
    }
