
from __future__ import annotations
import json,tempfile
from pathlib import Path
from typing import Any
from .phase16_verified_update import validate_verified_update,run_phase16
CONFIRM_PHRASE="PUBLISH_VERIFIED_UPDATE"
def preview_verified_update(*,repo_root,database_path,payload:dict[str,Any])->dict[str,Any]:
    u=validate_verified_update(payload)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"u.json"; p.write_text(json.dumps([payload],ensure_ascii=False),encoding="utf-8")
        r=run_phase16(repo_root=repo_root,database_path=database_path,verified_updates_path=p,commit=False)
    return {"status":"ok","validated":True,"update":{"place_id":u.place_id,"field_name":u.field_name,"value":u.value,
            "source_name":u.source_name,"source_url":u.source_url,"observed_at":u.observed_at},
            "dry_run":r,"canonical_write":False,"publication":False}
def commit_verified_update(*,repo_root,database_path,payload:dict[str,Any],confirm:str)->dict[str,Any]:
    if confirm!=CONFIRM_PHRASE: raise ValueError("explicit publication confirmation required")
    validate_verified_update(payload)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"u.json"; p.write_text(json.dumps([payload],ensure_ascii=False),encoding="utf-8")
        return run_phase16(repo_root=repo_root,database_path=database_path,verified_updates_path=p,commit=True)
