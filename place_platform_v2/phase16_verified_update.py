from __future__ import annotations
import hashlib,json,shutil,sqlite3
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlparse
from uuid import UUID,uuid5

from .controlled_canonical_adoption import apply_controlled_canonical_adoption
from .controlled_production_publication import (
    commit_controlled_production_publication,
    plan_controlled_production_publication,
    rollback_controlled_production_publication,
)
from .post_publication_verification import verify_post_publication

POLICY_VERSION="16-verified-update-controlled-publication-v1"
ALLOWED_FIELDS=frozenset({"phone","website"})
_NS=UUID("d1d28c04-4171-47aa-a094-acde05c55d64")

@dataclass(frozen=True)
class VerifiedUpdate:
    place_id:str
    field_name:str
    value:str
    source_name:str
    source_url:str
    observed_at:str
    operator_note:str=""

def _sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def _http(v:str)->bool:
    try:
        p=urlparse(str(v or "").strip())
        return p.scheme in {"http","https"} and bool(p.netloc)
    except Exception:
        return False

def validate_verified_update(raw:dict[str,Any])->VerifiedUpdate:
    if not isinstance(raw,dict): raise ValueError("verified update must be object")
    if raw.get("trust_tier")!="operator_verified_independent_source":
        raise ValueError("operator verified independent source required")
    if raw.get("community_report") is True:
        raise ValueError("community report cannot be adopted directly")
    pid=str(raw.get("place_id") or "").strip()
    field=str(raw.get("field_name") or "").strip()
    value=str(raw.get("value") or "").strip()
    name=str(raw.get("source_name") or "").strip()
    url=str(raw.get("source_url") or "").strip()
    observed=str(raw.get("observed_at") or "").strip()
    if not pid or not name or not observed: raise ValueError("required field missing")
    if field not in ALLOWED_FIELDS: raise ValueError("field not allowed")
    if field=="website" and not _http(value): raise ValueError("website must be http(s)")
    if not value: raise ValueError("value is empty")
    if not _http(url): raise ValueError("source_url must be http(s)")
    community_url=str(raw.get("community_source_url") or "").strip()
    if community_url and community_url==url: raise ValueError("source is not independent")
    try: dt=datetime.fromisoformat(observed.replace("Z","+00:00"))
    except Exception as e: raise ValueError("observed_at must be ISO-8601") from e
    if dt.tzinfo is None: raise ValueError("observed_at must be timezone-aware")
    return VerifiedUpdate(pid,field,value,name,url,dt.astimezone(timezone.utc).isoformat(),
                          str(raw.get("operator_note") or "").strip())

def load_verified_updates(path:str|Path)->tuple[VerifiedUpdate,...]:
    p=Path(path)
    if not p.exists(): return ()
    data=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data,list): raise ValueError("verified update file must be array")
    return tuple(validate_verified_update(x) for x in data)

def _eid(u:VerifiedUpdate)->str:
    m="|".join((u.place_id,u.field_name,u.value,u.source_url,u.observed_at))
    return str(uuid5(_NS,m))

def persist_verified_evidence(database_path:str|Path,updates:tuple[VerifiedUpdate,...],*,commit=False)->dict[str,Any]:
    db=Path(database_path); before=_sha(db)
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    inserted=existing=0; decisions=[]
    try:
        con.execute("BEGIN IMMEDIATE")
        for u in updates:
            if con.execute("select 1 from places where place_id=?",(u.place_id,)).fetchone() is None:
                raise ValueError(f"canonical place missing:{u.place_id}")
            eid=_eid(u)
            if con.execute("select 1 from place_evidence where evidence_id=?",(eid,)).fetchone():
                existing+=1; decisions.append({"evidence_id":eid,"outcome":"already_present"}); continue
            md={"persistence":"phase3_5_controlled_web_evidence",
                "phase16_policy_version":POLICY_VERSION,
                "trust_tier":"operator_verified_independent_source",
                "community_direct_adoption":False,
                "operator_note":u.operator_note}
            con.execute("""insert into place_evidence(
                evidence_id,place_id,source_type,source_name,source_record_id,source_url,
                source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json
            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid,u.place_id,"web",u.source_name,eid,u.source_url,u.observed_at,"contact",
             u.field_name,json.dumps(u.value,ensure_ascii=False),"supported",u.observed_at,
             json.dumps(md,ensure_ascii=False,sort_keys=True)))
            inserted+=1; decisions.append({"evidence_id":eid,"outcome":"inserted"})
        con.commit() if commit else con.rollback()
    except Exception:
        con.rollback(); raise
    finally:
        con.close()
    return {"mode":"COMMIT" if commit else "DRY_RUN",
            "inserted_count":inserted if commit else 0,
            "would_insert_count":inserted if not commit else 0,
            "already_present_count":existing,"decisions":decisions,
            "database_unchanged":before==_sha(db)}

def _backup_db(db:Path,bdir:Path):
    bdir.mkdir(parents=True,exist_ok=False)
    dst=bdir/db.name; shutil.copy2(db,dst); return dst,_sha(dst)

def _restore_db(db:Path,backup:Path,h:str):
    tmp=db.with_name(db.name+".tmp-phase16")
    shutil.copy2(backup,tmp); tmp.replace(db)
    if _sha(db)!=h: raise RuntimeError("canonical rollback hash mismatch")

def run_phase16(*,repo_root,database_path,verified_updates_path,backup_root=None,commit=False):
    root=Path(repo_root).resolve(); db=Path(database_path).resolve()
    updates=load_verified_updates(verified_updates_path)
    if not updates:
        return {"policy_version":POLICY_VERSION,"mode":"COMMIT" if commit else "DRY_RUN",
                "status":"NO_ELIGIBLE_VERIFIED_UPDATE","verified_update_count":0,
                "canonical_mutation":False,"production_mutation":False,
                "safety":{"community_direct_adoption":False,
                          "independent_verification_required":True,
                          "trust_policy_lowered":False}}
    dry=persist_verified_evidence(db,updates,commit=False)
    if not dry["database_unchanged"]: raise RuntimeError("evidence dry-run changed DB")
    if not commit:
        with TemporaryDirectory() as td:
            fixture=Path(td)/db.name; shutil.copy2(db,fixture)
            persist_verified_evidence(fixture,updates,commit=True)
            adoption=apply_controlled_canonical_adoption(database_path=fixture,commit=False)
        return {"policy_version":POLICY_VERSION,"mode":"DRY_RUN",
                "status":"READY" if adoption.get("apply_outcome_counts",{}).get("ready",0) else "BLOCKED",
                "evidence_dry_run":dry,"adoption_dry_run":adoption,
                "canonical_mutation":False,"production_mutation":False,
                "safety":{"community_direct_adoption":False,
                          "independent_verification_required":True,
                          "trust_policy_lowered":False}}
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bbase=Path(backup_root).resolve() if backup_root else root/"data/v2/phase16_backups"
    bdir=bbase/(stamp+"-verified-update"); dbbak,dbhash=_backup_db(db,bdir)
    release=None
    try:
        evidence=persist_verified_evidence(db,updates,commit=True)
        pre=apply_controlled_canonical_adoption(database_path=db,commit=False)
        counts=pre.get("apply_outcome_counts",{})
        if counts.get("blocked",0) or not counts.get("ready",0):
            raise RuntimeError(f"adoption blocked:{counts}")
        adopted=apply_controlled_canonical_adoption(database_path=db,commit=True)
        if adopted.get("updated_field_count",0)<1: raise RuntimeError("zero canonical updates")
        plan=plan_controlled_production_publication(repo_root=root,database_path=db)
        if plan.get("status") not in {"READY_TO_PUBLISH","ALREADY_PUBLISHED"}:
            raise RuntimeError("publication blocked:"+repr(plan.get("blockers")))
        published=commit_controlled_production_publication(repo_root=root,database_path=db)
        release=published.get("release_id")
        post=verify_post_publication(root)
        if post.get("status")!="PASS": raise RuntimeError("post publication verification failed")
        return {"policy_version":POLICY_VERSION,"mode":"COMMIT","status":"PUBLISHED",
                "evidence_commit":evidence,"adoption_dry_run":pre,"adoption_commit":adopted,
                "publication_plan":plan,"publication_commit":published,"post_publication":post,
                "canonical_backup_dir":str(bdir),"canonical_rollback_available":True,
                "publication_rollback_available":bool(published.get("rollback_available")),
                "safety":{"community_direct_adoption":False,
                          "independent_verification_required":True,
                          "automatic_unverified_publication":False,
                          "trust_policy_lowered":False}}
    except Exception:
        if release:
            rollback_controlled_production_publication(repo_root=root,release_id=release)
        _restore_db(db,dbbak,dbhash)
        raise
