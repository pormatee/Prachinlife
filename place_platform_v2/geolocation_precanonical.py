from __future__ import annotations
import json,sqlite3,hashlib,uuid,re
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

POLICY_VERSION="4.11-geolocation-precanonical-v1"
_NAMESPACE=uuid.UUID("33596d18-4e0b-4720-85c2-710416c79470")

def _load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def _norm(v):return re.sub(r"[^0-9a-zก-๙]+","",str(v or "").casefold(),flags=re.I)
def _cid(key):return str(uuid.uuid5(_NAMESPACE,"candidate|"+key))
def _eid(key,o):return str(uuid.uuid5(_NAMESPACE,"evidence|"+key+"|"+str(o.get("source_family"))+"|"+str(o.get("source_url"))+"|"+str(o.get("evidence_kind"))))

SCHEMA=(
"""CREATE TABLE IF NOT EXISTS precanonical_candidates (
candidate_id TEXT PRIMARY KEY,candidate_key TEXT NOT NULL UNIQUE,proposed_name TEXT NOT NULL,
province TEXT NOT NULL,category TEXT NOT NULL,identity_outcome TEXT NOT NULL,
independent_source_family_count INTEGER NOT NULL,lifecycle_conflict_json TEXT NOT NULL,
status TEXT NOT NULL,policy_version TEXT NOT NULL,created_at TEXT NOT NULL)""",
"""CREATE TABLE IF NOT EXISTS precanonical_evidence (
evidence_id TEXT PRIMARY KEY,candidate_id TEXT NOT NULL REFERENCES precanonical_candidates(candidate_id) ON DELETE RESTRICT,
source_type TEXT NOT NULL,source_name TEXT NOT NULL,source_family TEXT NOT NULL,source_record_id TEXT,
source_url TEXT,observed_name TEXT NOT NULL,province TEXT NOT NULL,phone TEXT,website TEXT,lifecycle_status TEXT,
evidence_kind TEXT NOT NULL,payload_json TEXT NOT NULL,policy_version TEXT NOT NULL,created_at TEXT NOT NULL)""",
)

def verify_geolocation_and_persist(*,database_path,identity_report_path,identity_evidence_path,geolocation_observations_path,commit=False)->dict[str,Any]:
    db=Path(database_path);before=db.read_bytes()
    ident=_load(identity_report_path);ie=_load(identity_evidence_path);geo=_load(geolocation_observations_path)
    verified=[x for x in ident.get("decisions",[]) if x.get("identity_outcome")=="VERIFIED_IDENTITY"]
    con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.execute("PRAGMA foreign_keys=ON")
    place_count_before=con.execute("select count(*) from places").fetchone()[0]
    outputs=[];insc=inse=alreadyc=alreadye=0

    for d in verified:
        name=d["name"];province=d["province"];key=d["candidate_key"]
        g=[o for o in geo if _norm(o.get("candidate_name"))==_norm(name) and str(o.get("province") or "").strip()==province]
        candidate_address=[o for o in g if o.get("evidence_kind")=="candidate_address_location"]
        landmark=[o for o in g if o.get("evidence_kind")=="landmark_geolocation_reference"]
        address_supported=bool(candidate_address and all(str(o.get("district") or "")=="ศรีมหาโพธิ" and str(o.get("subdistrict") or "")=="ท่าตูม" for o in candidate_address))
        exact_candidate_coords=any(o.get("latitude") is not None and o.get("longitude") is not None and o.get("coordinate_owner") in (None,"candidate") for o in candidate_address)
        if exact_candidate_coords:
            geo_outcome="EXACT_COORDINATES_VERIFIED"
        elif address_supported:
            geo_outcome="ADDRESS_LOCATION_VERIFIED_COORDINATES_UNRESOLVED"
        else:
            geo_outcome="GEOLOCATION_INSUFFICIENT"

        identity_obs=[o for o in ie if _norm(o.get("candidate_name"))==_norm(name)]
        persistence_obs=identity_obs+g
        if commit and geo_outcome!="GEOLOCATION_INSUFFICIENT":
            con.execute("BEGIN")
            for st in SCHEMA:con.execute(st)
            cid=_cid(key)
            cur=con.execute("""INSERT OR IGNORE INTO precanonical_candidates
              (candidate_id,candidate_key,proposed_name,province,category,identity_outcome,
               independent_source_family_count,lifecycle_conflict_json,status,policy_version,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
              (cid,key,name,province,d.get("category") or "vegetarian","VERIFIED_IDENTITY",
               int(d.get("independent_source_family_count") or 0),"[]",
               "verified_identity_address_location",POLICY_VERSION,datetime.now(timezone.utc).isoformat()))
            if cur.rowcount:insc+=1
            else:alreadyc+=1
            for o in persistence_obs:
                eid=_eid(key,o)
                cur=con.execute("""INSERT OR IGNORE INTO precanonical_evidence
                  (evidence_id,candidate_id,source_type,source_name,source_family,source_record_id,source_url,
                   observed_name,province,phone,website,lifecycle_status,evidence_kind,payload_json,policy_version,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (eid,cid,str(o.get("source_type") or "web"),str(o.get("source_name") or ""),
                   str(o.get("source_family") or ""),str(o.get("source_record_id") or "") or None,
                   str(o.get("source_url") or "") or None,str(o.get("observed_name") or o.get("candidate_name") or ""),
                   province,str(o.get("phone") or "") or None,str(o.get("website") or "") or None,
                   str(o.get("lifecycle_status") or "") or None,str(o.get("evidence_kind") or "identity"),
                   json.dumps(o,ensure_ascii=False,sort_keys=True),POLICY_VERSION,datetime.now(timezone.utc).isoformat()))
                if cur.rowcount:inse+=1
                else:alreadye+=1
            con.commit()
        outputs.append({
          "candidate_key":key,"name":name,"province":province,
          "geolocation_outcome":geo_outcome,
          "address_location_verified":address_supported,
          "exact_coordinates_verified":exact_candidate_coords,
          "landmark_reference_count":len(landmark),
          "canonical_adoption_ready":geo_outcome=="EXACT_COORDINATES_VERIFIED",
          "next_step":"acquire_exact_candidate_coordinates" if not exact_candidate_coords else "controlled_new_place_adoption_review",
        })

    place_count_after=con.execute("select count(*) from places").fetchone()[0]
    pc=con.execute("select count(*) from precanonical_candidates").fetchone()[0] if commit else None
    pe=con.execute("select count(*) from precanonical_evidence").fetchone()[0] if commit else None
    con.close();after=db.read_bytes()
    return {
      "status":"PASS","mode":"COMMIT" if commit else "DRY_RUN","policy_version":POLICY_VERSION,
      "verified_identity_input_count":len(verified),"results":outputs,
      "inserted_candidate_count":insc,"inserted_evidence_count":inse,
      "already_present_candidate_count":alreadyc,"already_present_evidence_count":alreadye,
      "precanonical_candidate_total":pc,"precanonical_evidence_total":pe,
      "safety":{"canonical_place_count_unchanged":place_count_before==place_count_after,
                "production_json_writes":False,"automatic_canonical_creation":False,
                "automatic_publication":False,"trust_policy_lowered":False,
                "landmark_coordinates_not_promoted_to_candidate":True,
                "database_changed_only_if_commit":(before!=after) if commit else before==after}
    }
