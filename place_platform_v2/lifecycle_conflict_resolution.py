from __future__ import annotations
import json,re,sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION="4.6-lifecycle-conflict-resolution-v1"
MIN_INDEPENDENT_LIFECYCLE_SOURCES=2

def _norm_phone(v):
    d=re.sub(r"\D+","",str(v or ""))
    if d.startswith("66") and len(d)>=10:d="0"+d[2:]
    return d

def _norm_name(v):
    return re.sub(r"[\W_]+","",str(v or "").casefold(),flags=re.UNICODE)

def resolve_lifecycle_conflict(*,database_path,fresh_observations_path)->dict[str,Any]:
    obs=json.loads(Path(fresh_observations_path).read_text(encoding="utf-8"))
    if not isinstance(obs,list):raise ValueError("fresh observations must be a list")
    con=sqlite3.connect(Path(database_path));con.row_factory=sqlite3.Row
    before=Path(database_path).read_bytes()
    candidates=[dict(r) for r in con.execute("select * from precanonical_candidates order by candidate_id")]
    decisions=[]
    for c in candidates:
        ev=[dict(r) for r in con.execute("select * from precanonical_evidence where candidate_id=?",(c["candidate_id"],))]
        known_phones={_norm_phone(x["phone"]) for x in ev if _norm_phone(x["phone"])}
        candidate_name=_norm_name(c["proposed_name"])
        matched=[];excluded=[]
        for o in obs:
            if str(o.get("province") or "").strip()!=str(c["province"] or "").strip():continue
            if _norm_name(o.get("candidate_name"))!=candidate_name:continue
            scope=str(o.get("identity_scope") or "").strip()
            phone=_norm_phone(o.get("phone"))
            observed=_norm_name(o.get("observed_name"))
            phone_match=bool(phone and phone in known_phones)
            name_related=bool(candidate_name and (candidate_name in observed or observed in candidate_name))
            if scope=="possible_other_branch" or (phone and known_phones and not phone_match):
                excluded.append({**o,"exclusion_reason":"branch_or_phone_identity_mismatch"})
                continue
            if not phone_match and not name_related:
                excluded.append({**o,"exclusion_reason":"insufficient_identity_match"})
                continue
            matched.append(o)

        lifecycle=[o for o in matched if str(o.get("lifecycle_status") or "").strip()]
        by_status={}
        for o in lifecycle:
            st=str(o["lifecycle_status"]).strip().casefold()
            by_status.setdefault(st,set()).add(str(o.get("source_family") or "").strip().casefold())
        lifecycle_counts={k:len(v) for k,v in sorted(by_status.items())}
        all_families={f for v in by_status.values() for f in v}

        if len(by_status)==1 and len(all_families)>=MIN_INDEPENDENT_LIFECYCLE_SOURCES:
            resolved=next(iter(by_status))
            outcome="RESOLVED"
            next_step="rerun_controlled_new_place_adoption_review"
        elif len(by_status)>1:
            resolved=None
            outcome="UNRESOLVED_CONFLICTING_FRESH_EVIDENCE"
            next_step="direct_operator_or_merchant_confirmation"
        else:
            resolved=None
            outcome="UNRESOLVED_NEEDS_DIRECT_CONFIRMATION"
            next_step="direct_operator_or_merchant_confirmation"

        decisions.append({
          "candidate_id":c["candidate_id"],"name":c["proposed_name"],"province":c["province"],
          "matched_fresh_observation_count":len(matched),
          "fresh_lifecycle_observation_count":len(lifecycle),
          "fresh_lifecycle_source_family_count":len(all_families),
          "fresh_lifecycle_status_support":lifecycle_counts,
          "excluded_observations":excluded,
          "resolution_outcome":outcome,"resolved_lifecycle":resolved,
          "next_step":next_step,
        })
    after=Path(database_path).read_bytes();con.close()
    counts=Counter(x["resolution_outcome"] for x in decisions)
    return {
      "status":"PASS","policy_version":POLICY_VERSION,"candidate_count":len(candidates),
      "decision_counts":dict(sorted(counts.items())),"decisions":decisions,
      "safety":{"database_unchanged":before==after,"database_writes":False,
                "canonical_writes":False,"precanonical_writes":False,
                "production_json_writes":False,"automatic_lifecycle_resolution":False,
                "branch_identity_guard_enforced":True,"trust_policy_lowered":False}
    }
