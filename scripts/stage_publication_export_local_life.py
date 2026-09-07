from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
    p.add_argument("--province", default="ปราจีนบุรี")
    p.add_argument("--write-stage", action="store_true")
    args, unknown = p.parse_known_args()

    cmd = [
        sys.executable,
        str(ROOT / "scripts/stage_publication_export.py"),
        "--database",
        str(args.database),
        "--province",
        args.province,
    ]
    if args.write_stage:
        cmd.append("--write-stage")
    cmd.extend(unknown)

    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode:
        raise SystemExit(proc.returncode)

    if not args.write_stage:
        return 0

    enabled = str(
        os.environ.get("PRACHIN_LOCAL_LIFE_TRUST_PUBLICATION_V1", "")
    ).strip().casefold() in {"1","true","yes","on","enabled"}
    if not enabled:
        print("LOCAL_LIFE_STAGE_BRIDGE=DISABLED")
        return 0

    from place_platform_v2.local_life_stage_bridge_v1 import (
        bridge_local_life_unmapped_places,
    )

    report = bridge_local_life_unmapped_places(
        ROOT / args.database if not Path(args.database).is_absolute() else Path(args.database),
        args.province,
        ROOT / "data/v2/staging/user_web",
    )
    print("LOCAL_LIFE_STAGE_BRIDGE=PASS")
    print("LOCAL_LIFE_STAGE_BRIDGE_REPORT=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["unmapped_eligible_place_ids"]:
        print("FINAL_RESULT=FAIL")
        print("FAIL_REASON=LOCAL_LIFE_UNMAPPED_ELIGIBLE_REMAIN")
        return 20
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
