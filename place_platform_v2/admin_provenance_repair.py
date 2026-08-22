"""Phase 2V.3.3 targeted provenance repair for committed admin evidence."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import json, shutil, sqlite3, tempfile

from .admin_drafts import AdminDraftStore
from .controlled_adoption import _draft_evidence, file_sha256
from .controlled_candidate_adoption import _latest_approved_create

POLICY_VERSION = "2V.3.3-admin-provenance-v1"

@dataclass(frozen=True)
class ProvenanceRepairItem:
    evidence_id: str
    field_name: str
    before_source_type: str
    before_source_name: str
    after_source_type: str
    after_source_name: str

@dataclass(frozen=True)
class ProvenanceRepairReport:
    mode: str
    policy_version: str
    draft_id: str
    place_id: str | None
    result: str
    repair_count: int
    repairs: tuple[ProvenanceRepairItem, ...]
    canonical_fields_unchanged: bool
    publication_performed: bool
    canonical_hash_before: str
    canonical_hash_after: str
    def to_dict(self): return asdict(self)

def _load_approved(draft_database: Path, draft_id: str):
    with tempfile.TemporaryDirectory(prefix="prachinlife-2v33-") as td:
        copy=Path(td)/"drafts.sqlite3"; shutil.copy2(draft_database, copy)
        with AdminDraftStore(copy) as store:
            item=_latest_approved_create(store,draft_id)
            if item is None: raise ValueError("draft must be latest approved create_place_candidate")
            evidence=_draft_evidence(item)
            return item, evidence

def _row_source(row):
    return {"source_type":row["source_type"],"source_name":row["source_name"],"source_record_id":row["source_record_id"],"source_url":row["source_url"]}

def _canonical_snapshot(con, place_id):
    row=con.execute("SELECT * FROM places WHERE place_id=?",(place_id,)).fetchone()
    return dict(row) if row else None

def _assess(canonical_database: Path, draft_database: Path, draft_id: str):
    _, desired_evidence=_load_approved(draft_database,draft_id)
    desired={e.evidence_id:e for e in desired_evidence if e.metadata.get("provenance_origin")=="operator_change"}
    uri=f"file:{canonical_database.resolve()}?mode=ro"; con=sqlite3.connect(uri,uri=True); con.row_factory=sqlite3.Row
    try:
        receipt=con.execute("SELECT place_id,evidence_ids_json FROM admin_adoption_receipts WHERE draft_id=?",(draft_id,)).fetchone()
        if receipt is None: raise ValueError("draft has no committed adoption receipt")
        place_id=str(receipt["place_id"]); raw_receipt_ids=json.loads(receipt["evidence_ids_json"])
        if isinstance(raw_receipt_ids, dict) and raw_receipt_ids.get("__type__") == "tuple":
            raw_receipt_ids = raw_receipt_ids.get("items") or []
        receipt_ids=set(raw_receipt_ids)
        repairs=[]; details=[]
        for eid,e in desired.items():
            if eid not in receipt_ids: continue
            row=con.execute("SELECT * FROM place_evidence WHERE evidence_id=? AND place_id=?",(eid,place_id)).fetchone()
            if row is None: raise ValueError(f"committed evidence missing: {eid}")
            current_meta=json.loads(row["metadata_json"])
            desired_meta=dict(current_meta); desired_meta.update(dict(e.metadata))
            after={"source_type":e.source.source_type.value,"source_name":e.source.source_name,"source_record_id":e.source.source_record_id,"source_url":e.source.source_url,"metadata":desired_meta}
            before={**_row_source(row),"metadata":current_meta}
            if before != after:
                repairs.append(ProvenanceRepairItem(eid,e.field_name,row["source_type"],row["source_name"],e.source.source_type.value,e.source.source_name))
                details.append((eid,before,after))
        return place_id, tuple(repairs), tuple(details), _canonical_snapshot(con,place_id)
    finally: con.close()

def assess_admin_provenance_repair(*, canonical_database, draft_database, draft_id):
    canonical_database=Path(canonical_database); draft_database=Path(draft_database); before=file_sha256(canonical_database)
    place_id,repairs,_,snap=_assess(canonical_database,draft_database,draft_id)
    after=file_sha256(canonical_database)
    return ProvenanceRepairReport("DRY_RUN",POLICY_VERSION,draft_id,place_id,"repairable" if repairs else "no_repair_needed",len(repairs),repairs,True,False,before,after)

def commit_admin_provenance_repair(*, canonical_database, draft_database, draft_id, repaired_at=None):
    canonical_database=Path(canonical_database); draft_database=Path(draft_database); before_hash=file_sha256(canonical_database)
    place_id,repairs,details,before_place=_assess(canonical_database,draft_database,draft_id)
    when=repaired_at or datetime.now(timezone.utc)
    if when.tzinfo is None: raise ValueError("repaired_at must be timezone-aware")
    if not repairs:
        return ProvenanceRepairReport("COMMIT",POLICY_VERSION,draft_id,place_id,"no_repair_needed",0,(),True,False,before_hash,file_sha256(canonical_database))
    con=sqlite3.connect(canonical_database); con.row_factory=sqlite3.Row
    try:
        with con:
            con.execute('''CREATE TABLE IF NOT EXISTS admin_provenance_repairs (repair_id TEXT PRIMARY KEY,draft_id TEXT NOT NULL,place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,evidence_ids_json TEXT NOT NULL,before_json TEXT NOT NULL,after_json TEXT NOT NULL,policy_version TEXT NOT NULL,repaired_at TEXT NOT NULL)''')
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_provenance_repairs_draft ON admin_provenance_repairs(draft_id)")
            existing=con.execute("SELECT 1 FROM admin_provenance_repairs WHERE draft_id=?",(draft_id,)).fetchone()
            if existing: raise ValueError("provenance repair audit already exists for draft")
            for eid,b,a in details:
                con.execute("UPDATE place_evidence SET source_type=?,source_name=?,source_record_id=?,source_url=?,metadata_json=? WHERE evidence_id=? AND place_id=?",(a["source_type"],a["source_name"],a["source_record_id"],a["source_url"],json.dumps(a["metadata"],ensure_ascii=False,sort_keys=True),eid,place_id))
            con.execute("INSERT INTO admin_provenance_repairs(repair_id,draft_id,place_id,evidence_ids_json,before_json,after_json,policy_version,repaired_at) VALUES(?,?,?,?,?,?,?,?)",(str(uuid4()),draft_id,place_id,json.dumps([x.evidence_id for x in repairs]),json.dumps([d[1] for d in details],ensure_ascii=False,sort_keys=True),json.dumps([d[2] for d in details],ensure_ascii=False,sort_keys=True),POLICY_VERSION,when.isoformat()))
        after_place=_canonical_snapshot(con,place_id)
    finally: con.close()
    return ProvenanceRepairReport("COMMIT",POLICY_VERSION,draft_id,place_id,"repaired",len(repairs),repairs,before_place==after_place,False,before_hash,file_sha256(canonical_database))
