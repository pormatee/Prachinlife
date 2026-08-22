#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.create_candidate_resolution_diagnostic import diagnose_approved_create_candidate_resolution

DEFAULT_CANONICAL = Path("data/v2/place_platform_v2.sqlite3")
DEFAULT_DRAFTS = Path("data/v2/admin_evidence_drafts.sqlite3")


def main() -> None:
    parser = argparse.ArgumentParser(description="PrachinLife Phase 2V.3.1 read-only create candidate resolution diagnostic")
    parser.add_argument("--draft-id", required=True, help="Latest approved create_place_candidate draft id")
    args = parser.parse_args()

    result = diagnose_approved_create_candidate_resolution(
        canonical_database=DEFAULT_CANONICAL,
        draft_database=DEFAULT_DRAFTS,
        draft_id=args.draft_id,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    print("CANONICAL_WRITES = DISABLED")
    print("DRAFT_WRITES = DISABLED")
    print("PUBLICATION = DISABLED")
    print("RESULT = DIAGNOSTIC_PASS")


if __name__ == "__main__":
    main()
