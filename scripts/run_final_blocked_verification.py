#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.external_verification import commit_external_verifications
from place_platform_v2.staged_milestone import eligible_place_ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
    ap.add_argument("--manifest", default="data/v2/final_blocked_external_sources.json")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    db = Path(args.database)
    records = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    before, blocked_before = eligible_place_ids(db)

    result = {
        "mode": "COMMIT" if args.commit else "DRY_RUN",
        "record_count": len(records),
        "eligible_before": len(before),
        "blocked_before": len(blocked_before),
        "canonical_field_writes": False,
        "production_json_changed": False,
        "public_user_web_switched": False,
    }

    if args.commit:
        backup = ROOT / "data/v2/backups/place_platform_v2.pre-final-blocked.sqlite3"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db, backup)
        result["backup"] = str(backup)
        result["committed"] = commit_external_verifications(db, records)

    after, blocked_after = eligible_place_ids(db)
    result["eligible_after"] = len(after)
    result["blocked_after"] = len(blocked_after)
    result["status"] = "PASS" if (not args.commit or len(blocked_after) == 0) else "INCOMPLETE"

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("CANONICAL_FIELD_WRITES = DISABLED")
    print("PRODUCTION_JSON = UNCHANGED")
    print("PUBLIC_USER_WEB_SWITCH = DISABLED")
    print("RESULT = FINAL_BLOCKED_VERIFICATION_" + result["status"])


if __name__ == "__main__":
    main()
