from __future__ import annotations
import hashlib,json,re,sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION="4.15-coverage-batch2-v1"
DIET_TERMS=("อาหารเจ","เจ ","เจ-","มังสวิรัติ","vegetarian","vegan","plant based","plant-based")

def _norm(v):
    return re.sub(r"[^0-9a-zก-๙]+","",str(v or "").casefold(),flags=re.I)

def _phones(v):
    out=set()
    for token in re.findall(r"\+?\d[\d\s\-()]{6,}\d",str(v or "")):
        d=re.sub(r"\D","",token)
        if d.startswith("66") and len(d)>=10:d="0"+d[2:]
        if 8<=len(d)<=12:out.add(d)
    return out

def _key(name,province):
    return hashlib.sha256((_norm(name)+"|"+str(province or "").strip().casefold()).encode()).hexdigest()

def _dedicated_name(name):
    s=str(name or "").casefold()
    return any(t in s for t in DIET_TERMS)

def continue_coverage_batch2(*,database_path,observations_path,prior_batch_path=None,
                             prior_identity_report_path=None)->dict[str,Any]:
    db=Path(database_path);before=db.read_bytes()
    obs=json.loads(Path(observations_path).read_text(encoding="utf-8"))
    prior_batch={}
    if prior_batch_path and Path(prior_batch_path).exists():
        prior_batch=json.loads(Path(prior_batch_path).read_text(encoding="utf-8"))
    prior_ident={}
    if prior_identity_report_path and Path(prior_identity_report_path).exists():
        prior_ident=json.loads(Path(prior_identity_report_path).read_text(encoding="utf-8"))

    con=sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro",uri=True);con.row_factory=sqlite3.Row
    canonical=[dict(r) for r in con.execute("select place_id,canonical_name,province,phone from places")]
    prec=[dict(r) for r in con.execute("select candidate_id,candidate_key,proposed_name,province,status from precanonical_candidates")]
    pending=[dict(r) for r in con.execute("""select q.candidate_id,c.proposed_name,c.province,q.status,q.reason,q.current_state,q.next_action
      from precanonical_pending_review q join precanonical_candidates c on c.candidate_id=q.candidate_id
      where q.status like 'pending_%'""")]
    con.close()

    known_names=set()
    for x in prior_batch.get("batch_results",[]):
        known_names.add((str(x.get("province") or "").strip(),_norm(x.get("name"))))
    for x in prior_ident.get("decisions",[]):
        known_names.add((str(x.get("province") or "").strip(),_norm(x.get("name"))))

    groups={}
    for o in obs:
        g=str(o.get("candidate_group") or _key(o.get("name"),o.get("province")))
        groups.setdefault(g,[]).append(o)

    results=[]
    for _,rows in groups.items():
        first=rows[0];name=str(first.get("name") or "").strip();province=str(first.get("province") or "").strip()
        phones=set()
        families=set()
        for o in rows:
            phones|=_phones(o.get("phone"))
            fam=str(o.get("source_family") or "").strip().casefold()
            if fam:families.add(fam)
        n=_norm(name)
        canon=[]
        for p in canonical:
            pn=_norm(p.get("canonical_name"))
            pp=_phones(p.get("phone"))
            same_name=bool(n and pn and n==pn and str(p.get("province") or "").strip()==province)
            phone_match=bool(phones & pp)
            if same_name or phone_match:
                canon.append({"place_id":p["place_id"],"canonical_name":p["canonical_name"],
                              "same_name":same_name,"phone_match":phone_match})
        pend=[p for p in pending if str(p.get("province") or "").strip()==province and _norm(p.get("proposed_name"))==n]
        pre=[p for p in prec if str(p.get("province") or "").strip()==province and _norm(p.get("proposed_name"))==n]
        known=(province,n) in known_names

        dedicated=_dedicated_name(name) or any(str(o.get("discovery_signal") or "") in {"dedicated_name","named_jay_report"} for o in rows)
        category_only=not dedicated and any("อาหารเจ" in str(o.get("source_category") or "") for o in rows)

        if canon:
            state="EXISTING_CANONICAL";next_step="attach_existing_evidence_if_useful"
        elif pend:
            state="PENDING_REVIEW";next_step="skip_pending_candidate"
        elif pre:
            state="PRECANONICAL_EXISTING";next_step="continue_precanonical_workflow"
        elif known:
            state="KNOWN_CANDIDATE";next_step="continue_identity_evidence_acquisition"
        elif category_only:
            state="NEW_CATEGORY_CANDIDATE";next_step="confirm_diet_scope_and_acquire_independent_source"
        else:
            state="NEW_DEDICATED_CANDIDATE";next_step="acquire_independent_identity_source"

        results.append({
          "candidate_key":_key(name,province),"name":name,"province":province,
          "batch_state":state,"next_step":next_step,
          "source_observation_count":len(rows),"independent_source_family_count":len(families),
          "source_families":sorted(families),"phones":sorted(phones),
          "dedicated_diet_signal":dedicated,"category_only_signal":category_only,
          "primary_directory_ready":False,
          "canonical_matches":canon,"pending_matches":pend,"precanonical_matches":pre,
          "observations":rows
        })

    order={"NEW_DEDICATED_CANDIDATE":0,"NEW_CATEGORY_CANDIDATE":1,"KNOWN_CANDIDATE":2,
           "EXISTING_CANONICAL":3,"PRECANONICAL_EXISTING":4,"PENDING_REVIEW":5}
    results.sort(key=lambda x:(order.get(x["batch_state"],99),x["name"]))
    counts=Counter(x["batch_state"] for x in results)
    queue=[{
      "candidate_key":x["candidate_key"],"name":x["name"],"province":x["province"],
      "candidate_scope":"dedicated" if x["batch_state"]=="NEW_DEDICATED_CANDIDATE" else "category_only",
      "independent_source_family_count":x["independent_source_family_count"],
      "next_step":x["next_step"]
    } for x in results if x["batch_state"] in {"NEW_DEDICATED_CANDIDATE","NEW_CATEGORY_CANDIDATE"}]

    after=db.read_bytes()
    return {
      "status":"PASS","policy_version":POLICY_VERSION,
      "source_observation_count":sum(x["source_observation_count"] for x in results),
      "candidate_group_count":len(results),"batch_state_counts":dict(sorted(counts.items())),
      "new_candidate_count":len(queue),"followup_queue_count":len(queue),
      "pending_candidate_count":sum(x["batch_state"]=="PENDING_REVIEW" for x in results),
      "results":results,"followup_queue":queue,"discovery_continues":True,
      "quality":{"category_only_candidates_not_promoted_to_primary":True,
                 "dedicated_scope_requires_identity_verification":True},
      "safety":{"database_unchanged":before==after,"database_writes":False,
                "canonical_writes":False,"precanonical_writes":False,"pending_queue_writes":False,
                "production_json_writes":False,"automatic_adoption":False,
                "automatic_publication":False,"pending_candidates_do_not_block_discovery":True,
                "trust_policy_lowered":False}
    }
