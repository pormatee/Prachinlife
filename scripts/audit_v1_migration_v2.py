#!/usr/bin/env python3
"""Read-only V1 production JSON migration audit for PrachinLife V2."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.migration_audit import audit_v1_files, discover_v1_place_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="V1 JSON files to audit")
    parser.add_argument("--root", default=str(ROOT), help="repo root used for auto-discovery")
    parser.add_argument("--json-out", help="optional output report path")
    args = parser.parse_args()

    paths = tuple(Path(p) for p in args.paths) if args.paths else discover_v1_place_json(args.root)
    report = audit_v1_files(paths)
    payload = report.to_dict()

    print("===== PRACHINLIFE V1 -> V2 DRY-RUN MIGRATION AUDIT =====")
    print(f"files_audited={payload['summary']['files_audited']}")
    print(f"total_records={payload['summary']['total_records']}")
    print(f"ready_records={payload['summary']['ready_records']}")
    print(f"skipped_records={payload['summary']['skipped_records']}")
    print(f"invalid_records={payload['summary']['invalid_records']}")
    print(f"duplicate_candidate_groups={payload['summary']['duplicate_candidate_groups']}")
    print(f"unreadable_files={payload['summary']['unreadable_files']}")
    for item in payload["files"]:
        print(
            f"FILE {item['path']} total={item['total']} ready={item['ready']} "
            f"skipped={item['skipped']} invalid={item['invalid']} missing_location={item['missing_location']} "
            f"missing_province={item['missing_province']} missing_categories={item['missing_categories']}"
        )
        key_counts = item.get("top_level_keys", {})
        keys = sorted(key_counts, key=lambda key: (-key_counts[key], key))[:20]
        print("  keys=" + ",".join(f"{key}:{key_counts[key]}" for key in keys))
    if payload["duplicate_candidate_groups"]:
        print("===== DUPLICATE CANDIDATE GROUPS =====")
        for group in payload["duplicate_candidate_groups"]:
            print(f"candidate_key={group['candidate_key']} occurrences={group['occurrences']}")
            for record in group["records"]:
                print(f"  {record}")

    if payload["unreadable_files"]:
        print("===== UNREADABLE / UNSUPPORTED =====")
        for path, reason in payload["unreadable_files"].items():
            print(f"{path}: {reason}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
