#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.staged_milestone import (
    acquire_osm_queue,
    commit_current_observations,
    eligible_place_ids,
    select_identity_anchor_queue,
)

POLICY_VERSION = "identity-anchor-rollout-v2-resumable"


def _fetcher(timeout: float):
    def fetch(url: str) -> bytes:
        return urllib.request.urlopen(url, timeout=timeout).read()
    return fetch


def acquire_item(item, *, retries=1, retry_delay=0.5, timeout=6.0):
    last = None
    for attempt in range(retries + 1):
        last = acquire_osm_queue([item], fetcher=_fetcher(timeout))[0]
        if last.get("status") != "acquisition_error":
            return last
        if attempt < retries and retry_delay:
            time.sleep(retry_delay)
    return last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
    ap.add_argument("--province", default="ปราจีนบุรี")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--retry-delay", type=float, default=0.5)
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--commit-observations", "--commit", action="store_true")
    ap.add_argument(
        "--report",
        default="data/v2/discovery_reports/identity_anchor_rollout_current.json",
    )
    args = ap.parse_args()

    before_eligible, before_blocked = eligible_place_ids(args.database, args.province)
    queue = select_identity_anchor_queue(
        args.database,
        province=args.province,
        limit=args.limit,
    )

    print(f"QUEUE = {len(queue)}", flush=True)
    print(f"MODE = {'COMMIT_STAGING' if args.commit_observations else 'READ_ONLY'}", flush=True)
    print(f"TIMEOUT = {max(1.0, args.timeout):.1f}s", flush=True)
    print(f"BATCH_SIZE = {max(1, args.batch_size)}", flush=True)

    observations = []
    committed = []
    batch_good = []
    batch_size = max(1, args.batch_size)

    for index, item in enumerate(queue, 1):
        print(
            f"[{index}/{len(queue)}] {item['osm_type']} {item['osm_id']} | {item['canonical_name']}",
            flush=True,
        )
        obs = acquire_item(
            item,
            retries=max(0, args.retries),
            retry_delay=max(0.0, args.retry_delay),
            timeout=max(1.0, args.timeout),
        )
        observations.append(obs)
        print(f"  -> {obs.get('status')} | {obs.get('reason', '')}", flush=True)

        if obs.get("status") == "current_listing":
            batch_good.append(obs)

        end_of_batch = index % batch_size == 0 or index == len(queue)
        if args.commit_observations and end_of_batch and batch_good:
            newly = commit_current_observations(args.database, batch_good)
            committed.extend(newly)
            print(
                f"  CHECKPOINT COMMIT = {len(newly)} (TOTAL {len(committed)})",
                flush=True,
            )
            batch_good = []

    statuses = Counter(x.get("status") for x in observations)
    after_eligible, after_blocked = eligible_place_ids(args.database, args.province)

    report = {
        "policy_version": POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "COMMIT_STAGING" if args.commit_observations else "READ_ONLY",
        "province": args.province,
        "queue_count": len(queue),
        "queue_object_types": dict(Counter(x["osm_type"] for x in queue)),
        "acquisition_statuses": dict(statuses),
        "committed_count": len(committed),
        "eligible_before": len(before_eligible),
        "eligible_after": len(after_eligible),
        "blocked_before": len(before_blocked),
        "blocked_after": len(after_blocked),
        "unresolved": [
            {
                "place_id": x.get("place_id"),
                "canonical_name": x.get("canonical_name"),
                "osm_type": x.get("osm_type"),
                "osm_id": x.get("osm_id"),
                "status": x.get("status"),
                "reason": x.get("reason"),
            }
            for x in observations
            if x.get("status") != "current_listing"
        ],
        "canonical_fields_changed": False,
        "production_json_changed": False,
        "public_user_web_switched": False,
        "resumable": True,
    }

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n===== SUMMARY =====", flush=True)
    print(f"ACQUISITION = {dict(statuses)}", flush=True)
    print(f"COMMITTED = {len(committed)}", flush=True)
    print(f"ELIGIBLE = {len(after_eligible)}", flush=True)
    print(f"BLOCKED = {len(after_blocked)}", flush=True)
    print("CANONICAL_FIELD_WRITES = DISABLED", flush=True)
    print("PRODUCTION_JSON = UNCHANGED", flush=True)
    print("PUBLIC_USER_WEB_SWITCH = DISABLED", flush=True)
    print("RESULT = IDENTITY_ANCHOR_ROLLOUT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
