#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.controlled_adoption import build_controlled_adoption_dry_run, report_json
from place_platform_v2.controlled_adoption_commit import commit_approved_draft

CANONICAL = ROOT / "data/v2/place_platform_v2.sqlite3"
DRAFTS = ROOT / "data/v2/admin_evidence_drafts.sqlite3"
BACKUPS = ROOT / "data/v2/backups"


def main() -> int:
    parser = argparse.ArgumentParser(description="PrachinLife Phase 2V.2 controlled canonical adoption")
    parser.add_argument("--draft-id", help="Latest approved update draft id to commit")
    parser.add_argument("--commit", action="store_true", help="Explicitly commit one approved draft")
    args = parser.parse_args()

    if not args.commit:
        print(report_json(build_controlled_adoption_dry_run(canonical_database=CANONICAL, draft_database=DRAFTS)))
        print("RESULT = DRY_RUN_ONLY")
        return 0
    if not args.draft_id:
        parser.error("--commit requires --draft-id")

    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUPS / f"place_platform_v2.pre-2v2-{stamp}.sqlite3"
    shutil.copy2(CANONICAL, backup)
    try:
        result = commit_approved_draft(
            canonical_database=CANONICAL, draft_database=DRAFTS, draft_id=args.draft_id
        )
    except Exception:
        shutil.copy2(backup, CANONICAL)
        print(f"ROLLBACK = {backup}", file=sys.stderr)
        raise

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print(f"BACKUP = {backup}")
    print("PUBLICATION = DISABLED")
    print("RESULT = CONTROLLED_COMMIT_PASS" if result.result in {"committed", "already_committed"} else "RESULT = NO_CANONICAL_CHANGE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
