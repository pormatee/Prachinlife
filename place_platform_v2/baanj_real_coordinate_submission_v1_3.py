
from __future__ import annotations
import hashlib, json, sqlite3
from pathlib import Path
from urllib.parse import urlparse

from place_platform_v2.precanonical_evidence_persistence import persist_verified_precanonical_evidence
from place_platform_v2.controlled_new_place_adoption_core_v2 import run_controlled_new_place_adoption_core_v2
from place_platform_v2.human_place_evidence import submit_coordinate_evidence

TARGET_NAME="Baan J Veggie House"
TARGET_PROVINCE="ปทุมธานี"
TARGET_LAT=14.076182
TARGET_LON=100.633498

def build_verified_inputs(*, source_report_path, adapter_path, observations_path):
    payload=json.loads(Path(source_report_path).read_text(encoding="utf-8"))
    rows=[x for x in payload.get("candidates",[])
          if str(x.get("name") or "").strip()==TARGET_NAME
          and str(x.get("province") or "").strip()==TARGET_PROVINCE]
    if len(rows)!=1:
        raise RuntimeError(f"expected exactly one frozen verified Baan J candidate, got {len(rows)}")
    c=rows[0]
    if c.get("verification_outcome")!="ready_for_controlled_review" or c.get("identity_status")!="new_identity":
        raise RuntimeError("frozen Baan J candidate is not verified new identity")
    families=sorted({str(x).strip().casefold() for x in c.get("source_families",[]) if str(x).strip()})
    if len(families)<2:
        raise RuntimeError("independent source-family quorum below 2")
    ck=hashlib.sha256(f"{TARGET_NAME.casefold()}|{TARGET_PROVINCE.casefold()}".encode()).hexdigest()
    decision={
      "candidate_key":ck,"name":TARGET_NAME,"province":TARGET_PROVINCE,
      "identity_outcome":"VERIFIED_IDENTITY","next_step":"persist_precanonical_evidence",
      "independent_source_family_count":len(families),"source_families":families,
      "accepted_observation_count":len(c.get("sources") or []),"blocked_observations":[],
      "phone":None,"phone_independent_source_family_count":0,"canonical_duplicate_matches":[],
      "lifecycle_conflicts":[],"identity_verified":True,
    }
    obs=[]
    for s in c.get("sources") or []:
        fam=str(s.get("family") or "").strip().casefold()
        url=str(s.get("url") or "").strip()
        rid=hashlib.sha256(f"{TARGET_NAME}|{TARGET_PROVINCE}|{fam}|{url}".encode()).hexdigest()[:24]
        obs.append({
          "candidate_name":TARGET_NAME,"observed_name":TARGET_NAME,"province":TARGET_PROVINCE,
          "source_type":"web","source_name":urlparse(url).netloc.casefold() or fam,
          "source_family":fam,"source_record_id":"baanj-real-v13-"+rid,"source_url":url,
          "evidence_kind":"identity","evidence_text":s.get("evidence_text"),
          "lifecycle_status":None,"phone":None,"website":None,
        })
    Path(adapter_path).write_text(json.dumps({
      "status":"PASS","policy_version":"baanj-real-coordinate-pilot-v1.3",
      "candidate_count":1,"decision_counts":{"VERIFIED_IDENTITY":1},
      "decisions":[decision],"ready_for_precanonical_evidence_count":1,
      "needs_more_evidence_count":0,
    },ensure_ascii=False,indent=2),encoding="utf-8")
    Path(observations_path).write_text(json.dumps(obs,ensure_ascii=False,indent=2),encoding="utf-8")
    return ck

def _candidate_id_for_key(db, candidate_key):
    con=sqlite3.connect(db)
    try:
        row=con.execute("select candidate_id from precanonical_candidates where candidate_key=?",(candidate_key,)).fetchone()
        if not row: raise RuntimeError("persisted Baan J precanonical candidate not found")
        return row[0]
    finally: con.close()

def run_real_submission(*, database_path, source_report_path, adapter_path, observations_path,
                        coordinate_report_paths=()):
    con=sqlite3.connect(database_path)
    before_ids={r[0] for r in con.execute("select place_id from places")}
    before_count=len(before_ids)
    con.close()

    ck=build_verified_inputs(source_report_path=source_report_path,
        adapter_path=adapter_path,observations_path=observations_path)
    persisted=persist_verified_precanonical_evidence(
        database_path=database_path,verification_report_path=adapter_path,
        evidence_observations_path=observations_path,commit=True)
    if persisted.get("status")!="PASS": raise RuntimeError("precanonical persistence failed")
    cid=_candidate_id_for_key(database_path,ck)

    adoption=run_controlled_new_place_adoption_core_v2(
        database_path=database_path,coordinate_report_paths=coordinate_report_paths,
        commit=True,candidate_ids=[cid])
    if not adoption.get("scoped_commit") or adoption.get("requested_candidate_ids") != [cid]:
        raise RuntimeError("Core V2 adoption did not honor exact candidate scope")
    rows=[x for x in adoption.get("decisions",[]) if str(x.get("candidate_id"))==cid]
    if len(rows)!=1: raise RuntimeError("scoped adoption did not return exactly one Baan J decision")
    d=rows[0]
    if d.get("outcome")!="READY_CANONICAL_COORDINATE_PENDING":
        raise RuntimeError(f"Baan J is not coordinate-pending: {d}")

    con=sqlite3.connect(database_path); con.row_factory=sqlite3.Row
    try:
        matches=con.execute("select * from places where canonical_name=? and province=?",
                            (TARGET_NAME,TARGET_PROVINCE)).fetchall()
        if len(matches)!=1: raise RuntimeError(f"expected one Baan J canonical shell, got {len(matches)}")
        place=matches[0]; pid=place["place_id"]
        after_ids={r[0] for r in con.execute("select place_id from places")}
        added=after_ids-before_ids
        if added!={pid}:
            raise RuntimeError(f"Baan J-only violation: expected one added place {pid}, added={sorted(added)}")
        if len(after_ids)!=before_count+1:
            raise RuntimeError("place count changed by more than exactly one")
        if place["latitude"] is not None or place["longitude"] is not None:
            raise RuntimeError("canonical coordinate populated before human review")
    finally: con.close()

    submission=submit_coordinate_evidence(
      database_path=database_path,place_id=pid,latitude=TARGET_LAT,longitude=TARGET_LON,
      source_kind="user",source_name="PrachinLife User Coordinate Submission",
      evidence_note="User-supplied exact coordinate for Baan J Veggie House; pending admin review.",
      source_reference="interactive-user-submission:2026-08-25",
      metadata={"pilot":"baanj-real-human-coordinate-v1.3",
                "coordinate_owner_claim":"candidate_exact_pin",
                "requires_admin_review":True})
    con=sqlite3.connect(database_path); con.row_factory=sqlite3.Row
    try:
        p=con.execute("select latitude,longitude from places where place_id=?",(pid,)).fetchone()
        q=con.execute("""select status,reviewed_at,applied_at,value_json
                         from human_place_evidence_queue where submission_id=?""",
                      (submission["submission_id"],)).fetchone()
        if tuple(p)!=(None,None): raise RuntimeError("canonical coordinate changed before admin review")
        if q["status"]!="pending_review" or q["reviewed_at"] is not None or q["applied_at"] is not None:
            raise RuntimeError("submission is not pending_review")
        coord=json.loads(q["value_json"])
    finally: con.close()
    return {
      "status":"PASS","place_id":pid,"candidate_id":cid,
      "submission_id":submission["submission_id"],"submitted_coordinate":coord,
      "review_status":"pending_review","canonical_coordinate":None,
      "near_me_enabled":False,"place_count_before":before_count,
      "place_count_after":before_count+1,"added_place_ids":[pid],
      "automatic_approval":False,"automatic_publication":False,
      "trust_policy_lowered":False,
    }
