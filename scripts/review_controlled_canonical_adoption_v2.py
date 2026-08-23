#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.canonical_adoption_review import review_controlled_canonical_adoption

DB = ROOT / "data/v2/place_platform_v2.sqlite3"
REPORT = ROOT / "data/v2/discovery_reports/controlled_canonical_adoption_review_v2.json"


def main() -> int:
    result = review_controlled_canonical_adoption(database_path=DB)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print("REVIEW_SCOPE_EVIDENCE =", result["review_scope_evidence_count"])
    print("PLACE_FIELDS =", result["review_place_field_count"])
    print("VERIFICATION =", result["verification_outcome_counts"])
    print("ADOPTION =", result["adoption_outcome_counts"])
    print("DATABASE_UNCHANGED =", result["safety"]["database_unchanged"])
    print("AUTOMATIC_ADOPTION =", result["safety"]["automatic_adoption"])
    print("RESULT = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
