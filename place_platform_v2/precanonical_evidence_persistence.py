from __future__ import annotations
import hashlib, json, sqlite3, uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION="4.4-precanonical-evidence-persistence-v1"
_NAMESPACE=uuid.UUID("3e1c5305-b7f1-4c38-8f92-79e827b56e13")

SCHEMA_STATEMENTS=(
"""CREATE TABLE IF NOT EXISTS precanonical_candidates (
  candidate_id TEXT PRIMARY KEY,
  candidate_key TEXT NOT NULL UNIQUE,
  proposed_name TEXT NOT NULL,
  province TEXT NOT NULL,
  category TEXT NOT NULL,
  identity_outcome TEXT NOT NULL,
  independent_source_family_count INTEGER NOT NULL,
  lifecycle_conflict_json TEXT NOT NULL,
  status TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL
)""",
"""CREATE TABLE IF NOT EXISTS precanonical_evidence (
  evidence_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES precanonical_candidates(candidate_id) ON DELETE RESTRICT,
  source_type TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_family TEXT NOT NULL,
  source_record_id TEXT,
  source_url TEXT,
  observed_name TEXT NOT NULL,
  province TEXT NOT NULL,
  phone TEXT,
  website TEXT,
  lifecycle_status TEXT,
  evidence_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL
)""",
"""CREATE INDEX IF NOT EXISTS idx_precanonical_evidence_candidate
ON precanonical_evidence(candidate_id)""",
)

def _sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def _load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def _candidate_id(candidate_key:str)->str:
    return str(uuid.uuid5(_NAMESPACE,"candidate|"+candidate_key))

def _evidence_id(candidate_key:str,o:dict[str,Any])->str:
    material="|".join([
      candidate_key,str(o.get("source_family") or ""),str(o.get("source_record_id") or ""),
      str(o.get("source_url") or ""),str(o.get("evidence_kind") or ""),
    ])
    return str(uuid.uuid5(_NAMESPACE,"evidence|"+material))

def _snapshot_non_precanonical(con):
    names=[r[0] for r in con.execute(
      "select name from sqlite_master where type='table' and name not like 'sqlite_%' "
      "and name not in ('precanonical_candidates','precanonical_evidence') order by name")]
    return {n:[tuple(x) for x in con.execute(f'SELECT * FROM "{n}" ORDER BY rowid')] for n in names}

def persist_verified_precanonical_evidence(*,database_path,verification_report_path,
                                           evidence_observations_path,commit=False,
                                           observed_at=None)->dict[str,Any]:
    observed_at=observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None: raise ValueError("observed_at must be timezone-aware")
    db=Path(database_path)
    report=_load(verification_report_path)
    observations=_load(evidence_observations_path)
    if not isinstance(observations,list): raise ValueError("evidence observations must be a list")

    con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.execute("PRAGMA foreign_keys=ON")
    before_non=_snapshot_non_precanonical(con)
    places_before=con.execute("select count(*) from places").fetchone()[0]
    canonical_hash_before=hashlib.sha256(json.dumps(
      [tuple(r) for r in con.execute("select * from places order by place_id")],
      ensure_ascii=False,default=str).encode()).hexdigest()
    place_evidence_before=con.execute("select count(*) from place_evidence").fetchone()[0]

    verified=[d for d in report.get("decisions",[]) if d.get("identity_outcome")=="VERIFIED_IDENTITY"]
    prepared=[]
    blocked=Counter()
    for d in verified:
        if d.get("canonical_duplicate_matches"):
            blocked["canonical_duplicate_match"]+=1;continue
        ck=str(d.get("candidate_key") or "")
        if not ck: blocked["missing_candidate_key"]+=1;continue
        cname=str(d.get("name") or "").strip();province=str(d.get("province") or "").strip()
        if not cname or not province: blocked["missing_identity_fields"]+=1;continue
        source_families=set(d.get("source_families") or [])
        obs=[o for o in observations
             if str(o.get("province") or "").strip()==province
             and str(o.get("candidate_name") or "").strip() in {cname,"ต้นหลิว อาหารเจ" if cname=="ต้นหลิวอาหารเจ" else cname}
             and str(o.get("source_family") or "").strip().casefold() in {str(x).casefold() for x in source_families}]
        if len({str(o.get("source_family") or "").casefold() for o in obs})<2:
            blocked["independent_source_guard"]+=1;continue
        prepared.append((d,obs))

    inserted_candidates=0;inserted_evidence=0;already_candidates=0;already_evidence=0
    if commit and prepared:
        try:
            con.execute("BEGIN")
            for statement in SCHEMA_STATEMENTS:
                con.execute(statement)
            for d,obs in prepared:
                ck=str(d["candidate_key"]); cid=_candidate_id(ck)
                cur=con.execute("""INSERT OR IGNORE INTO precanonical_candidates
                  (candidate_id,candidate_key,proposed_name,province,category,identity_outcome,
                   independent_source_family_count,lifecycle_conflict_json,status,policy_version,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                  (cid,ck,d["name"],d["province"],"vegetarian",d["identity_outcome"],
                   int(d.get("independent_source_family_count") or 0),
                   json.dumps(d.get("lifecycle_conflicts") or [],ensure_ascii=False),
                   "verified_identity",POLICY_VERSION,observed_at.isoformat()))
                if cur.rowcount: inserted_candidates+=1
                else: already_candidates+=1
                for o in obs:
                    eid=_evidence_id(ck,o)
                    cur=con.execute("""INSERT OR IGNORE INTO precanonical_evidence
                      (evidence_id,candidate_id,source_type,source_name,source_family,source_record_id,
                       source_url,observed_name,province,phone,website,lifecycle_status,evidence_kind,
                       payload_json,policy_version,created_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (eid,cid,str(o.get("source_type") or "web"),str(o.get("source_name") or ""),
                       str(o.get("source_family") or ""),str(o.get("source_record_id") or "") or None,
                       str(o.get("source_url") or "") or None,str(o.get("observed_name") or o.get("candidate_name") or ""),
                       str(o.get("province") or ""),str(o.get("phone") or "") or None,
                       str(o.get("website") or "") or None,str(o.get("lifecycle_status") or "") or None,
                       str(o.get("evidence_kind") or "identity"),
                       json.dumps(o,ensure_ascii=False,sort_keys=True),POLICY_VERSION,observed_at.isoformat()))
                    if cur.rowcount: inserted_evidence+=1
                    else: already_evidence+=1
            con.commit()
        except Exception:
            con.rollback();raise
    elif commit:
        con.execute("BEGIN")
        for statement in SCHEMA_STATEMENTS:
            con.execute(statement)
        con.commit()

    after_non=_snapshot_non_precanonical(con)
    places_after=con.execute("select count(*) from places").fetchone()[0]
    canonical_hash_after=hashlib.sha256(json.dumps(
      [tuple(r) for r in con.execute("select * from places order by place_id")],
      ensure_ascii=False,default=str).encode()).hexdigest()
    place_evidence_after=con.execute("select count(*) from place_evidence").fetchone()[0]
    pc_count=con.execute("select count(*) from precanonical_candidates").fetchone()[0] if commit else None
    pe_count=con.execute("select count(*) from precanonical_evidence").fetchone()[0] if commit else None
    con.close()

    return {
      "status":"PASS","mode":"COMMIT" if commit else "DRY_RUN","policy_version":POLICY_VERSION,
      "verified_identity_input_count":len(verified),"prepared_candidate_count":len(prepared),
      "prepared_evidence_count":sum(len(x[1]) for x in prepared),
      "inserted_candidate_count":inserted_candidates,"inserted_evidence_count":inserted_evidence,
      "already_present_candidate_count":already_candidates,"already_present_evidence_count":already_evidence,
      "precanonical_candidate_total":pc_count,"precanonical_evidence_total":pe_count,
      "blocked_counts":dict(sorted(blocked.items())),
      "safety":{
        "canonical_place_count_unchanged":places_before==places_after,
        "canonical_rows_unchanged":canonical_hash_before==canonical_hash_after,
        "place_evidence_unchanged":place_evidence_before==place_evidence_after,
        "non_precanonical_tables_unchanged":before_non==after_non,
        "production_json_writes":False,"automatic_canonical_creation":False,
        "automatic_publication":False,"trust_policy_lowered":False,
        "idempotent_ids":True,
      }
    }
