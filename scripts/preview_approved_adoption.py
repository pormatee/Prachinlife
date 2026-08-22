#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.controlled_adoption import build_controlled_adoption_dry_run, report_json


def main() -> int:
    parser = argparse.ArgumentParser(description="PrachinLife Phase 2V.1 approved adoption dry-run")
    parser.add_argument("--canonical-db", default="data/v2/place_platform_v2.sqlite3")
    parser.add_argument("--draft-db", default="data/v2/admin_evidence_drafts.sqlite3")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_controlled_adoption_dry_run(canonical_database=args.canonical_db, draft_database=args.draft_db)
    if args.json:
        print(report_json(report))
    else:
        print("===== PHASE 2V.1 CONTROLLED ADOPTION DRY-RUN =====")
        print("mode =", report.mode)
        print("policy =", report.policy_version)
        print("approved_groups =", report.approved_groups)
        print("adoptable_drafts =", report.adoptable_drafts)
        print("blocked_drafts =", report.blocked_drafts)
        print("proposed_field_changes =", report.proposed_field_changes)
        print("blocked_field_changes =", report.blocked_field_changes)
        for draft in report.drafts:
            print("\nDRAFT", draft.draft_id, draft.operation, "=>", draft.result)
            print(" reason:", draft.reason)
            for field in draft.fields:
                print(" ", field.field_name, field.verification_outcome, "=>", field.adoption_outcome)
            if draft.blocked_fields:
                print(" noncanonical_fields:", ", ".join(draft.blocked_fields))
        print("\ncanonical_hash_before =", report.canonical_hash_before)
        print("canonical_hash_after  =", report.canonical_hash_after)
        print("canonical_unchanged =", report.canonical_unchanged)
        print("draft_unchanged =", report.draft_unchanged)
        print("canonical_writes = DISABLED")
        print("publication = DISABLED")
        safe = report.canonical_unchanged and report.draft_unchanged
        print("RESULT =", "DRY_RUN_PASS" if safe else "FAIL")
    return 0 if (report.canonical_unchanged and report.draft_unchanged) else 2


if __name__ == "__main__":
    raise SystemExit(main())
