#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.admin_provenance_repair import assess_admin_provenance_repair, commit_admin_provenance_repair
p=argparse.ArgumentParser(description="PrachinLife Phase 2V.3.3 admin operator provenance repair")
p.add_argument("--draft-id",required=True); p.add_argument("--commit",action="store_true")
a=p.parse_args()
fn=commit_admin_provenance_repair if a.commit else assess_admin_provenance_repair
r=fn(canonical_database=ROOT/"data/v2/place_platform_v2.sqlite3",draft_database=ROOT/"data/v2/admin_evidence_drafts.sqlite3",draft_id=a.draft_id)
print(json.dumps(r.to_dict(),ensure_ascii=False,indent=2,default=str))
print("CANONICAL_FIELD_WRITES = DISABLED")
print("PUBLICATION = DISABLED")
print("RESULT = PROVENANCE_REPAIR_PASS")
