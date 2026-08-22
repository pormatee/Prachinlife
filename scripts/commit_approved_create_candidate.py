#!/usr/bin/env python3
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.controlled_candidate_adoption import assess_approved_create_candidate, commit_approved_create_candidate

CANONICAL=ROOT/"data/v2/place_platform_v2.sqlite3"
DRAFTS=ROOT/"data/v2/admin_evidence_drafts.sqlite3"
BACKUPS=ROOT/"data/v2/backups"


def main():
    parser=argparse.ArgumentParser(description="PrachinLife Phase 2V.3 approved create candidate adoption")
    parser.add_argument("--draft-id",required=True,help="Latest approved create_place_candidate draft id")
    parser.add_argument("--commit",action="store_true",help="Explicitly create the internal canonical place")
    args=parser.parse_args()
    if not args.commit:
        result=assess_approved_create_candidate(canonical_database=CANONICAL,draft_database=DRAFTS,draft_id=args.draft_id)
        print(json.dumps(result.to_dict(),ensure_ascii=False,indent=2,default=str))
        print("CANONICAL_WRITES = DISABLED")
        print("PUBLICATION = DISABLED")
        print("RESULT = DRY_RUN_PASS" if result.canonical_unchanged else "RESULT = FAIL")
        return 0 if result.canonical_unchanged else 2

    BACKUPS.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=BACKUPS/f"place_platform_v2.pre-2v3-{stamp}.sqlite3"
    shutil.copy2(CANONICAL,backup)
    try:
        result=commit_approved_create_candidate(canonical_database=CANONICAL,draft_database=DRAFTS,draft_id=args.draft_id)
    except Exception:
        shutil.copy2(backup,CANONICAL)
        print(f"ROLLBACK = {backup}",file=sys.stderr)
        raise
    print(json.dumps(result.to_dict(),ensure_ascii=False,indent=2,default=str))
    print(f"BACKUP = {backup}")
    print("PUBLICATION = DISABLED")
    print("RESULT = CREATE_CANDIDATE_COMMIT_PASS" if result.result in {"committed","already_committed"} else "RESULT = NO_CANONICAL_CHANGE")
    return 0

if __name__=="__main__": raise SystemExit(main())
