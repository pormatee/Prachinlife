#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.contracts import GeoPoint, SourceRef, SourceType
from place_platform_v2.geographic_correction import (
    GeographicCorrectionObservation,
    commit_proposal,
    evaluate_proposal,
    make_proposal,
)

DB = ROOT / "data/v2/place_platform_v2.sqlite3"


def _dt(value):
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    return parsed


def load_proposal(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    observations = []
    for item in data["observations"]:
        src = item["source"]
        observations.append(
            GeographicCorrectionObservation(
                source=SourceRef(
                    SourceType(src["source_type"]),
                    src["source_name"],
                    source_record_id=src.get("source_record_id"),
                    source_url=src.get("source_url"),
                    observed_at=_dt(src.get("observed_at")),
                ),
                place_name=item["place_name"],
                province=item["province"],
                location=GeoPoint(
                    float(item["location"]["latitude"]),
                    float(item["location"]["longitude"]),
                ),
            )
        )
    return make_proposal(
        place_id=data["place_id"],
        proposed_province=data["proposed_province"],
        observations=observations,
    )


def out(result):
    payload = {
        "mode": result.mode,
        "policy_version": result.policy_version,
        "place_id": result.place_id,
        "proposal_id": result.proposal_id,
        "result": result.result,
        "reason": result.reason,
        "province_before": result.province_before,
        "province_after": result.province_after,
        "supporting_lineages": list(result.supporting_lineages),
        "observation_count": result.observation_count,
        "evidence_ids": list(result.evidence_ids),
        "revision_id": result.revision_id,
        "canonical_fields_changed": list(result.canonical_fields_changed),
        "publication_performed": result.publication_performed,
        "user_web_switched": result.user_web_switched,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="PrachinLife Phase 2W.5 canonical geographic correction review")
    ap.add_argument("--proposal-json", required=True)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    proposal = load_proposal(Path(args.proposal_json))

    if not args.commit:
        result = evaluate_proposal(DB, proposal)
        out(result)
        print("CANONICAL_WRITES = DISABLED")
        print("PUBLICATION = DISABLED")
        print("USER_WEB_SWITCH = DISABLED")
        print("RESULT = PHASE2W5_DRY_RUN_PASS")
        return

    preview = evaluate_proposal(DB, proposal)
    if preview.result != "ready_to_commit":
        out(preview)
        raise SystemExit("COMMIT BLOCKED: proposal did not pass dry-run gate")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ROOT / "data/v2/backups" / f"place_platform_v2.pre-2w5-{stamp}.sqlite3"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB, backup)

    result = commit_proposal(DB, proposal)
    out(result)
    print(f"BACKUP = {backup}")
    print("PUBLICATION = DISABLED")
    print("USER_WEB_SWITCH = DISABLED")
    print("RESULT = PHASE2W5_COMMIT_PASS")


if __name__ == "__main__":
    main()
