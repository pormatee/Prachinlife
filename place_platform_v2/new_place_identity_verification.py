from __future__ import annotations
import hashlib, json, re, sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

POLICY_VERSION="4.3-independent-identity-verification-v1"
_NAME_RE=re.compile(r"[^0-9a-zก-๙]+",re.I)

def _sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def _norm_name(v):
    return _NAME_RE.sub("",str(v or "").casefold())

def _norm_phone(v):
    digits=re.sub(r"\D","",str(v or ""))
    if digits.startswith("66") and len(digits)>=10: digits="0"+digits[2:]
    return digits

def _host(url):
    try:
        h=(urlparse(str(url or "")).hostname or "").casefold()
        return h[4:] if h.startswith("www.") else h
    except Exception:return ""

def _candidate_key(name,province):
    return hashlib.sha256(("%s|%s"%(_norm_name(name),str(province or "").strip().casefold())).encode()).hexdigest()

def verify_new_place_candidates(database_path:str|Path, discovery_report:dict[str,Any],
                                evidence_observations:list[dict[str,Any]])->dict[str,Any]:
    db=Path(database_path); before=_sha(db)
    con=sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro",uri=True);con.row_factory=sqlite3.Row
    try:
        existing=list(con.execute("select place_id,canonical_name,province,phone,website,latitude,longitude from places"))
    finally:con.close()

    candidates=discovery_report.get("new_place_candidates") or []
    decisions=[]
    for c in candidates:
        key=_candidate_key(c.get("name"),c.get("province"))
        obs=[o for o in evidence_observations
             if _norm_name(o.get("candidate_name"))==_norm_name(c.get("name"))
             and str(o.get("province") or "").strip()==str(c.get("province") or "").strip()]
        accepted=[]; blocked=[]; family_values=defaultdict(set)
        candidate_phone=_norm_phone(c.get("phone"))
        for o in obs:
            url=str(o.get("source_url") or "")
            source_family=str(o.get("source_family") or _host(url) or o.get("source_name") or "").strip().casefold()
            oname=_norm_name(o.get("observed_name") or o.get("candidate_name"))
            if oname != _norm_name(c.get("name")):
                blocked.append({"reason":"name_conflict","source_url":url});continue
            if str(o.get("province") or "").strip()!=str(c.get("province") or "").strip():
                blocked.append({"reason":"province_conflict","source_url":url});continue
            phone=_norm_phone(o.get("phone"))
            value=("phone:"+phone) if phone else "existence"
            family_values[value].add(source_family)
            accepted.append({**o,"source_family":source_family})
        existence_families={x["source_family"] for x in accepted}
        phone_families=set()
        if candidate_phone:
            phone_families=family_values.get("phone:"+candidate_phone,set())

        # Cross-check full canonical DB again by normalized name/phone.
        duplicate_matches=[]
        for x in existing:
            same_province=str(x["province"] or "").strip()==str(c.get("province") or "").strip()
            same_name=_norm_name(x["canonical_name"])==_norm_name(c.get("name"))
            same_phone=bool(candidate_phone and _norm_phone(x["phone"])==candidate_phone)
            # Common/generic names must never collide across provinces.
            # A phone match is globally strong; a name match is only meaningful
            # inside the same province at this pre-canonical stage.
            if same_phone or (same_province and same_name):
                duplicate_matches.append({"place_id":x["place_id"],"canonical_name":x["canonical_name"],
                                          "province":x["province"],"same_province":same_province,
                                          "same_name":same_name,"same_phone":same_phone})
        if duplicate_matches:
            outcome="BLOCKED_EXISTING_CANONICAL"
            next_step="entity_resolution_review"
        elif len(existence_families)>=2:
            outcome="VERIFIED_IDENTITY"
            next_step="persist_precanonical_evidence"
        elif len(existence_families)==1:
            outcome="SUPPORTED_IDENTITY"
            next_step="acquire_second_independent_source"
        else:
            outcome="INSUFFICIENT_EVIDENCE"
            next_step="acquire_independent_source"

        lifecycle_conflicts=[]
        statuses={str(x.get("lifecycle_status") or "").strip().casefold() for x in accepted if x.get("lifecycle_status")}
        if "open" in statuses and ("closed" in statuses or "permanently_closed" in statuses):
            lifecycle_conflicts.append("open_vs_closed_source_conflict")

        decisions.append({
          "candidate_key":key,"name":c.get("name"),"province":c.get("province"),
          "identity_outcome":outcome,"next_step":next_step,
          "independent_source_family_count":len(existence_families),
          "source_families":sorted(existence_families),
          "accepted_observation_count":len(accepted),
          "blocked_observations":blocked,
          "phone":c.get("phone"),"phone_independent_source_family_count":len(phone_families),
          "canonical_duplicate_matches":duplicate_matches,
          "lifecycle_conflicts":lifecycle_conflicts,
          "identity_verified":outcome=="VERIFIED_IDENTITY",
        })
    after=_sha(db)
    counts=Counter(x["identity_outcome"] for x in decisions)
    return {
      "status":"PASS","policy_version":POLICY_VERSION,"candidate_count":len(candidates),
      "decision_counts":dict(sorted(counts.items())),"decisions":decisions,
      "ready_for_precanonical_evidence_count":sum(x["identity_outcome"]=="VERIFIED_IDENTITY" for x in decisions),
      "needs_more_evidence_count":sum(x["identity_outcome"] in {"SUPPORTED_IDENTITY","INSUFFICIENT_EVIDENCE"} for x in decisions),
      "safety":{"database_unchanged":before==after,"database_writes":False,"canonical_writes":False,
                "evidence_writes":False,"production_json_writes":False,"automatic_place_creation":False,
                "trust_policy_lowered":False,"source_family_independence_enforced":True,
                "province_agnostic":True}}
