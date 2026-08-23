from __future__ import annotations
import json,re,sqlite3
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher

POLICY_VERSION="4.10-batch-identity-verification-v1"

def _norm(v):
    return re.sub(r"[^0-9a-zก-๙]+","",str(v or "").casefold(),flags=re.I)

def _phone(v):
    d=re.sub(r"\D","",str(v or ""))
    if d.startswith("66") and len(d)>=10:d="0"+d[2:]
    return d

def _load(p):return json.loads(Path(p).read_text(encoding="utf-8"))

def _name_matches(candidate,observed):
    a=_norm(candidate);b=_norm(observed)
    if not a or not b:return False
    if a==b or a in b or b in a:return True
    return SequenceMatcher(None,a,b).ratio()>=0.78

def verify_batch_identities(*,database_path,batch_report_path,evidence_path)->dict[str,Any]:
    db=Path(database_path);before=db.read_bytes()
    batch=_load(batch_report_path);evidence=_load(evidence_path)
    queue=batch.get("verification_queue") or []
    con=sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro",uri=True);con.row_factory=sqlite3.Row
    canonical=[dict(r) for r in con.execute("select place_id,canonical_name,province,phone from places")]
    con.close()

    decisions=[]
    for q in queue:
        name=q["name"];province=q["province"]
        obs=[o for o in evidence if str(o.get("province") or "").strip()==province
             and _name_matches(name,o.get("candidate_name") or o.get("observed_name"))]
        accepted=[];blocked=[]
        for o in obs:
            if not _name_matches(name,o.get("observed_name") or o.get("candidate_name")):
                blocked.append({"reason":"name_conflict","source_url":o.get("source_url")});continue
            accepted.append(o)
        families=sorted({str(o.get("source_family") or "").strip().casefold() for o in accepted if o.get("source_family")})
        phones=Counter(_phone(o.get("phone")) for o in accepted if _phone(o.get("phone")))
        dup=[]
        for x in canonical:
            same_province=str(x.get("province") or "").strip()==province
            same_name=_norm(x.get("canonical_name"))==_norm(name)
            same_phone=bool(_phone(x.get("phone")) and _phone(x.get("phone")) in phones)
            if same_phone or (same_province and same_name):
                dup.append({"place_id":x["place_id"],"canonical_name":x["canonical_name"],
                            "same_name":same_name,"same_phone":same_phone})
        if dup:
            outcome="BLOCKED_EXISTING_CANONICAL"
            next_step="entity_resolution_review"
        elif len(families)>=2:
            outcome="VERIFIED_IDENTITY"
            next_step="acquire_geolocation_and_persist_precanonical_evidence"
        elif len(families)==1:
            outcome="SUPPORTED_IDENTITY"
            next_step="acquire_second_independent_source"
        else:
            outcome="INSUFFICIENT_EVIDENCE"
            next_step="acquire_independent_source"
        decisions.append({
          "candidate_key":q["candidate_key"],"name":name,"province":province,"category":q.get("category"),
          "identity_outcome":outcome,"next_step":next_step,
          "independent_source_family_count":len(families),"source_families":families,
          "accepted_observation_count":len(accepted),"blocked_observations":blocked,
          "phone_support":dict(phones),"canonical_duplicate_matches":dup,
          "geolocation_ready":False,
          "canonical_adoption_ready":False,
        })
    after=db.read_bytes();counts=Counter(x["identity_outcome"] for x in decisions)
    return {
      "status":"PASS","policy_version":POLICY_VERSION,"verification_queue_count":len(queue),
      "decision_counts":dict(sorted(counts.items())),"decisions":decisions,
      "verified_identity_count":counts["VERIFIED_IDENTITY"],
      "supported_identity_count":counts["SUPPORTED_IDENTITY"],
      "blocked_count":counts["BLOCKED_EXISTING_CANONICAL"],
      "ready_for_geolocation_count":sum(x["identity_outcome"]=="VERIFIED_IDENTITY" for x in decisions),
      "needs_more_identity_evidence_count":sum(x["identity_outcome"] in {"SUPPORTED_IDENTITY","INSUFFICIENT_EVIDENCE"} for x in decisions),
      "safety":{"database_unchanged":before==after,"database_writes":False,"canonical_writes":False,
                "precanonical_writes":False,"pending_queue_writes":False,"production_json_writes":False,
                "automatic_adoption":False,"automatic_publication":False,"trust_policy_lowered":False,
                "source_family_independence_enforced":True,"batch_processing":True}
    }
