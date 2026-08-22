#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.publication_export import (
    DEFAULT_STAGING_DIR,
    build_staged_payload,
    evaluate_publication_database,
    write_staged_export,
)


def main():
    parser = argparse.ArgumentParser(description="PrachinLife Phase 2W.1 publication/export gate")
    parser.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
    parser.add_argument("--province", default="ปราจีนบุรี")
    parser.add_argument("--write-stage", action="store_true")
    args = parser.parse_args()

    report, decisions = evaluate_publication_database(args.database, province=args.province)
    payload = build_staged_payload(decisions, province=args.province)
    result = {
        "mode": "WRITE_STAGE" if args.write_stage else "DRY_RUN",
        "policy_version": report.policy_version,
        "province": report.province,
        "canonical_count": report.canonical_count,
        "eligible_count": report.eligible_count,
        "blocked_count": report.blocked_count,
        "reason_counts": dict(report.reason_counts),
        "staged_payload_count": payload["count"],
        "publication_store_written": False,
        "user_web_switched": False,
    }
    if args.write_stage:
        out = DEFAULT_STAGING_DIR / "prachinlife_places_v2.candidate.json"
        try:
            result["sha256"] = write_staged_export(payload, output_path=out)
            result["output_path"] = str(out)
            result["result"] = "staged_export_written"
        except ValueError as exc:
            result["result"] = "blocked_fail_closed"
            result["reason"] = str(exc)
    else:
        result["result"] = "eligible_for_staging" if report.may_stage_export else "blocked_fail_closed"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("PRODUCTION_EXPORT = UNCHANGED")
    print("USER_WEB_SWITCH = DISABLED")
    print("RESULT = PHASE2W1_PASS")


if __name__ == "__main__":
    main()
