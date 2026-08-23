from __future__ import annotations
import json,sqlite3,uuid,math,re
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

POLICY_VERSION="4.13-direct-coordinate-confirmation-v1"
_NAMESPACE=uuid.UUID("8a8f6d10-f0af-43c6-a6cc-15b33e8f6f1d")
ALLOWED_METHODS={"map_pin","operator","merchant","in_person","admin"}
PRAJIN_LAT_RANGE=(13.6,14.6)
PRAJIN_LON_RANGE=(101.0,102.2)

SCHEMA=(
"""CREATE TABLE IF NOT EXISTS precanonical_direct_coordinates (
 confirmation_id TEXT PRIMARY KEY,
 candidate_id TEXT NOT NULL REFERENCES precanonical_candidates(candidate_id) ON DELETE RESTRICT,
 confirmer TEXT NOT NULL,
 confirmer_role TEXT NOT NULL,
 method TEXT NOT NULL,
 latitude REAL NOT NULL,
 longitude REAL NOT NULL,
 confirmed_at TEXT NOT NULL,
 reference TEXT NOT NULL,
 notes TEXT,
 payload_json TEXT NOT NULL,
 policy_version TEXT NOT NULL,
 created_at TEXT NOT NULL
)""",
"""CREATE INDEX IF NOT EXISTS idx_precanonical_direct_coordinates_candidate
 ON precanonical_direct_coordinates(candidate_id)""",
)

def _load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def _norm(v):return re.sub(r"[^0-9a-zก-๙]+","",str(v or "").casefold(),flags=re.I)
def _valid_iso(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return d.tzinfo is not None
    except Exception:return False
def _cid(candidate_id,p):
    raw="|".join([candidate_id,str(p.get("confirmer") or ""),str(p.get("method") or ""),
                  str(p.get("latitude") or ""),str(p.get("longitude") or ""),
                  str(p.get("confirmed_at") or ""),str(p.get("reference") or "")])
    return str(uuid.uuid5(_NAMESPACE,raw))

def confirm_direct_coordinates(*,database_path,confirmation_path,commit=False)->dict[str,Any]:
    db=Path(database_path);payload=_load(confirmation_path)
    con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.execute("PRAGMA foreign_keys=ON")
    before_places=[tuple(x) for x in con.execute("select * from places order by place_id")]
    before_candidates=[tuple(x) for x in con.execute("select * from precanonical_candidates order by candidate_id")]

    name=str(payload.get("candidate_name") or "").strip()
    province=str(payload.get("province") or "").strip()
    row=con.execute("select * from precanonical_candidates where proposed_name=? and province=?",(name,province)).fetchone()
    errors=[]
    if row is None:errors.append("candidate_not_found")
    confirmer=str(payload.get("confirmer") or "").strip()
    role=str(payload.get("confirmer_role") or "").strip()
    method=str(payload.get("method") or "").strip().casefold()
    reference=str(payload.get("reference") or "").strip()
    confirmed_at=str(payload.get("confirmed_at") or "").strip()
    if not confirmer:errors.append("missing_confirmer")
    if not role:errors.append("missing_confirmer_role")
    if method not in ALLOWED_METHODS:errors.append("invalid_method")
    if not reference:errors.append("missing_reference")
    if not _valid_iso(confirmed_at):errors.append("invalid_confirmed_at")
    try:
        lat=float(payload.get("latitude"));lon=float(payload.get("longitude"))
    except Exception:
        lat=lon=None;errors.append("invalid_coordinates")
    if lat is not None and not (5.0<=lat<=21.0 and 97.0<=lon<=106.5):
        errors.append("outside_thailand_bounds")
    if province=="ปราจีนบุรี" and lat is not None and not (PRAJIN_LAT_RANGE[0]<=lat<=PRAJIN_LAT_RANGE[1] and PRAJIN_LON_RANGE[0]<=lon<=PRAJIN_LON_RANGE[1]):
        errors.append("outside_prachinburi_context")

    confirmation_id=None;inserted=already=0
    if row is not None and not errors:
        confirmation_id=_cid(row["candidate_id"],payload)
        if commit:
            con.execute("BEGIN")
            for s in SCHEMA:con.execute(s)
            cur=con.execute("""INSERT OR IGNORE INTO precanonical_direct_coordinates
              (confirmation_id,candidate_id,confirmer,confirmer_role,method,latitude,longitude,
               confirmed_at,reference,notes,payload_json,policy_version,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (confirmation_id,row["candidate_id"],confirmer,role,method,lat,lon,confirmed_at,
               reference,str(payload.get("notes") or "") or None,
               json.dumps(payload,ensure_ascii=False,sort_keys=True),
               POLICY_VERSION,datetime.now(timezone.utc).isoformat()))
            inserted=1 if cur.rowcount else 0
            already=0 if cur.rowcount else 1
            con.commit()

    if errors:
        outcome="STILL_UNRESOLVED";resolved=False;next_step="supply_valid_direct_coordinate_confirmation"
    else:
        outcome="DIRECT_COORDINATES_CONFIRMED";resolved=True;next_step="controlled_new_place_adoption_review"

    total=None
    if commit:
        total=con.execute("select count(*) from precanonical_direct_coordinates").fetchone()[0]
    after_places=[tuple(x) for x in con.execute("select * from places order by place_id")]
    after_candidates=[tuple(x) for x in con.execute("select * from precanonical_candidates order by candidate_id")]
    con.close()
    return {
      "status":"PASS","mode":"COMMIT" if commit else "DRY_RUN","policy_version":POLICY_VERSION,
      "candidate_name":name,"province":province,"validation_errors":errors,
      "confirmation_outcome":outcome,"coordinates_resolved":resolved,
      "latitude":lat if not errors else None,"longitude":lon if not errors else None,
      "confirmation_id":confirmation_id,"inserted_confirmation_count":inserted,
      "already_present_confirmation_count":already,"direct_coordinate_total":total,
      "next_step":next_step,
      "safety":{"canonical_rows_unchanged":before_places==after_places,
                "precanonical_candidate_rows_unchanged":before_candidates==after_candidates,
                "production_json_writes":False,"automatic_coordinate_guessing":False,
                "automatic_canonical_creation":False,"automatic_publication":False,
                "direct_provenance_required":True,"trust_policy_lowered":False}
    }
