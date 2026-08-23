#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.evidence_acquisition import acquire_osm_contact_evidence


def main() -> int:
    p = argparse.ArgumentParser(description="Acquire candidate phone/website evidence from exact OSM objects for Phase 3.3")
    p.add_argument("--database", default=str(ROOT / "data/v2/place_platform_v2.sqlite3"))
    p.add_argument("--plan", default=str(ROOT / "data/v2/discovery_reports/targeted_production_enrichment_v2.json"))
    p.add_argument("--output", default=str(ROOT / "data/v2/discovery_reports/targeted_osm_evidence_acquisition_v2.json"))
    args = p.parse_args()

    report = acquire_osm_contact_evidence(
        database_path=args.database,
        targeted_plan_path=args.plan,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("===== PHASE 3.3 OSM EVIDENCE ACQUISITION =====")
    print("SOURCE_AVAILABLE =", report.get("source_available", True))
    print("ACQUISITION_COMPLETE =", report.get("acquisition_complete", True))
    print("TARGETS =", report["target_count"])
    print("MATCHED =", report["matched_target_count"])
    print("CANDIDATE_CLAIMS =", report["candidate_claim_count"])
    print("FIELDS =", report["candidate_field_counts"])
    print("BLOCKED =", report["blocked_counts"])
    print("DATABASE_UNCHANGED =", report["safety"]["database_unchanged"])
    print("TRUST_POLICY_LOWERED =", report["safety"]["trust_policy_lowered"])
    if report.get("source_available", True):
        print("RESULT = PASS")
    else:
        print("SOURCE_ERROR =", report.get("source_error"))
        print("RESULT = SAFE_SOURCE_UNAVAILABLE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
