from __future__ import annotations
import json, re, sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

POLICY_VERSION="4.5-controlled-new-place-adoption-review-v1"
MIN_INDEPENDENT_IDENTITY_SOURCES=2

def _norm_name(v):
    return re.sub(r"[\W_]+","",str(v or "").casefold(),flags=re.UNICODE)

def _norm_phone(v):
    d=re.sub(r"\D+","",str(v or ""))
    if d.startswith("66") and len(d)>=10:d="0"+d[2:]
    return d

def _snapshot(con):
    tables=[r[0] for r in con.execute(
      "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    return {t:[tuple(x) for x in con.execute(f'SELECT * FROM "{t}" ORDER BY rowid')] for t in tables}

def review_new_place_adoption(*,database_path)->dict[str,Any]:
    con=sqlite3.connect(Path(database_path));con.row_factory=sqlite3.Row
    before=_snapshot(con)
    candidates=[dict(r) for r in con.execute("select * from precanonical_candidates order by candidate_id")]
    decisions=[]
    counts=Counter()

    for c in candidates:
        ev=[dict(r) for r in con.execute(
          "select * from precanonical_evidence where candidate_id=? order by evidence_id",(c["candidate_id"],))]
        families=sorted({str(x["source_family"]).strip().casefold() for x in ev if x["source_family"]})
        observed_names={_norm_name(x["observed_name"]) for x in ev if x["observed_name"]}
        proposed=_norm_name(c["proposed_name"])
        phones=Counter(_norm_phone(x["phone"]) for x in ev if _norm_phone(x["phone"]))
        lifecycle=Counter(str(x["lifecycle_status"]).strip().casefold()
                          for x in ev if x["lifecycle_status"])
        conflicts=json.loads(c["lifecycle_conflict_json"] or "[]")

        duplicate_matches=[]
        for p in con.execute("select place_id,canonical_name,province,phone from places"):
            same_province=str(p["province"] or "").strip()==str(c["province"] or "").strip()
            same_name=_norm_name(p["canonical_name"])==proposed
            same_phone=bool(_norm_phone(p["phone"]) and _norm_phone(p["phone"]) in phones)
            if same_phone or (same_province and same_name):
                duplicate_matches.append({
                  "place_id":p["place_id"],"canonical_name":p["canonical_name"],
                  "same_province":same_province,"same_name":same_name,"same_phone":same_phone})

        blockers=[]
        review_flags=[]
        if c["identity_outcome"]!="VERIFIED_IDENTITY":
            blockers.append("identity_not_verified")
        if len(families)<MIN_INDEPENDENT_IDENTITY_SOURCES:
            blockers.append("insufficient_independent_sources")
        if proposed not in observed_names:
            blockers.append("proposed_name_not_observed")
        if duplicate_matches:
            blockers.append("canonical_duplicate_risk")
        if conflicts:
            review_flags.extend(conflicts)
        if len(lifecycle)>1:
            if "open" in lifecycle and "permanently_closed" in lifecycle:
                if "open_vs_closed_source_conflict" not in review_flags:
                    review_flags.append("open_vs_closed_source_conflict")
            else:
                review_flags.append("lifecycle_source_conflict")

        # Identity may be strong enough to create a canonical shell, but an unresolved
        # lifecycle conflict must never be silently converted into ACTIVE.
        if blockers:
            outcome="BLOCKED"
            next_step="resolve_blockers_before_adoption"
            proposed_lifecycle=None
        elif review_flags:
            outcome="NEEDS_REVIEW"
            next_step="resolve_lifecycle_before_canonical_adoption"
            proposed_lifecycle=None
        else:
            outcome="READY"
            next_step="controlled_canonical_adoption"
            proposed_lifecycle="active" if lifecycle.get("open",0)>0 else "unknown"

        counts[outcome]+=1
        decisions.append({
          "candidate_id":c["candidate_id"],"candidate_key":c["candidate_key"],
          "name":c["proposed_name"],"province":c["province"],"category":c["category"],
          "identity_outcome":c["identity_outcome"],
          "independent_source_family_count":len(families),"source_families":families,
          "evidence_count":len(ev),"phone_support":dict(phones),
          "lifecycle_observations":dict(lifecycle),"duplicate_matches":duplicate_matches,
          "blockers":blockers,"review_flags":sorted(set(review_flags)),
          "adoption_outcome":outcome,"proposed_lifecycle":proposed_lifecycle,
          "next_step":next_step,
        })

    after=_snapshot(con);con.close()
    return {
      "status":"PASS","policy_version":POLICY_VERSION,
      "candidate_count":len(candidates),"decision_counts":dict(sorted(counts.items())),
      "ready_count":counts["READY"],"needs_review_count":counts["NEEDS_REVIEW"],
      "blocked_count":counts["BLOCKED"],"decisions":decisions,
      "safety":{
        "database_unchanged":before==after,"canonical_writes":False,
        "precanonical_writes":False,"production_json_writes":False,
        "automatic_canonical_creation":False,"automatic_lifecycle_resolution":False,
        "automatic_publication":False,"trust_policy_lowered":False,
      }
    }
