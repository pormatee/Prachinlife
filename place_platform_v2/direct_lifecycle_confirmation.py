from __future__ import annotations
import json, sqlite3, uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION="4.7-direct-lifecycle-confirmation-v1"
_NAMESPACE=uuid.UUID("6619336a-3e46-4cb4-809d-9a82ac84ef84")
ALLOWED_RESULTS={"open","permanently_closed","unresolved"}
ALLOWED_METHODS={"phone","in_person","merchant","admin"}

SCHEMA_STATEMENTS=(
"""CREATE TABLE IF NOT EXISTS precanonical_direct_confirmations (
  confirmation_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES precanonical_candidates(candidate_id) ON DELETE RESTRICT,
  confirmer TEXT NOT NULL,
  confirmer_role TEXT NOT NULL,
  method TEXT NOT NULL,
  result TEXT NOT NULL,
  confirmed_at TEXT NOT NULL,
  contact_or_reference TEXT,
  notes TEXT,
  payload_json TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL
)""",
"""CREATE INDEX IF NOT EXISTS idx_precanonical_direct_confirmation_candidate
ON precanonical_direct_confirmations(candidate_id)""",
)

def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def _cid(candidate_id:str,payload:dict[str,Any])->str:
    material="|".join([
      candidate_id,str(payload.get("confirmer") or ""),str(payload.get("method") or ""),
      str(payload.get("result") or ""),str(payload.get("confirmed_at") or ""),
      str(payload.get("contact_or_reference") or "")
    ])
    return str(uuid.uuid5(_NAMESPACE,material))

def _valid_iso(value:str)->bool:
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        return dt.tzinfo is not None
    except Exception:
        return False

def evaluate_direct_confirmation(*,database_path,confirmation_path,commit=False)->dict[str,Any]:
    db=Path(database_path)
    payload=_load(confirmation_path)
    if not isinstance(payload,dict): raise ValueError("confirmation payload must be an object")
    con=sqlite3.connect(db);con.row_factory=sqlite3.Row;con.execute("PRAGMA foreign_keys=ON")
    before_places=[tuple(r) for r in con.execute("select * from places order by place_id")]
    before_pre=[tuple(r) for r in con.execute("select * from precanonical_candidates order by candidate_id")]

    candidate_name=str(payload.get("candidate_name") or "").strip()
    province=str(payload.get("province") or "").strip()
    row=con.execute("select * from precanonical_candidates where proposed_name=? and province=?",
                    (candidate_name,province)).fetchone()
    errors=[]
    if row is None:
        errors.append("candidate_not_found")

    result=str(payload.get("result") or "").strip().casefold()
    method=str(payload.get("method") or "").strip().casefold()
    confirmer=str(payload.get("confirmer") or "").strip()
    confirmer_role=str(payload.get("confirmer_role") or "").strip()
    confirmed_at=str(payload.get("confirmed_at") or "").strip()

    if not confirmer: errors.append("missing_confirmer")
    if not confirmer_role: errors.append("missing_confirmer_role")
    if method not in ALLOWED_METHODS: errors.append("invalid_method")
    if result not in ALLOWED_RESULTS: errors.append("invalid_result")
    if not _valid_iso(confirmed_at): errors.append("invalid_confirmed_at")
    if result in {"open","permanently_closed"} and not str(payload.get("contact_or_reference") or "").strip():
        errors.append("missing_contact_or_reference")

    inserted=0;already=0
    confirmation_id=None
    if row is not None and not errors:
        confirmation_id=_cid(row["candidate_id"],payload)
        if commit:
            con.execute("BEGIN")
            for st in SCHEMA_STATEMENTS: con.execute(st)
            cur=con.execute("""INSERT OR IGNORE INTO precanonical_direct_confirmations
             (confirmation_id,candidate_id,confirmer,confirmer_role,method,result,confirmed_at,
              contact_or_reference,notes,payload_json,policy_version,created_at)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
             (confirmation_id,row["candidate_id"],confirmer,confirmer_role,method,result,confirmed_at,
              str(payload.get("contact_or_reference") or "") or None,
              str(payload.get("notes") or "") or None,
              json.dumps(payload,ensure_ascii=False,sort_keys=True),POLICY_VERSION,
              datetime.now(timezone.utc).isoformat()))
            inserted=1 if cur.rowcount else 0
            already=0 if cur.rowcount else 1
            con.commit()

    after_places=[tuple(r) for r in con.execute("select * from places order by place_id")]
    after_pre=[tuple(r) for r in con.execute("select * from precanonical_candidates order by candidate_id")]

    # Confirmation does not mutate lifecycle itself. It only creates auditable direct evidence.
    if errors:
        outcome="STILL_UNRESOLVED"
        resolved=None
        next_step="supply_valid_direct_confirmation"
    elif result=="open":
        outcome="CONFIRMED_OPEN"
        resolved="open"
        next_step="rerun_controlled_new_place_adoption_review_with_confirmation"
    elif result=="permanently_closed":
        outcome="CONFIRMED_CLOSED"
        resolved="permanently_closed"
        next_step="rerun_controlled_new_place_adoption_review_with_confirmation"
    else:
        outcome="STILL_UNRESOLVED"
        resolved=None
        next_step="additional_direct_confirmation"

    total=None
    if commit:
        total=con.execute("select count(*) from precanonical_direct_confirmations").fetchone()[0]
    con.close()
    return {
      "status":"PASS","mode":"COMMIT" if commit else "DRY_RUN","policy_version":POLICY_VERSION,
      "candidate_name":candidate_name,"province":province,"validation_errors":errors,
      "confirmation_id":confirmation_id,"confirmation_outcome":outcome,
      "resolved_lifecycle":resolved,"next_step":next_step,
      "inserted_confirmation_count":inserted,"already_present_confirmation_count":already,
      "direct_confirmation_total":total,
      "safety":{
        "canonical_rows_unchanged":before_places==after_places,
        "precanonical_candidate_rows_unchanged":before_pre==after_pre,
        "production_json_writes":False,"automatic_canonical_creation":False,
        "automatic_lifecycle_mutation":False,"automatic_publication":False,
        "trust_policy_lowered":False,"direct_provenance_required":True,
      }
    }
