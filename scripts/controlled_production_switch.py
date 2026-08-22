#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.controlled_production_switch import (
    commit_production_switch,
    plan_production_switch,
    rollback_production_switch,
)

p = argparse.ArgumentParser(description="PrachinLife V2 controlled production switch")
p.add_argument("--database", default=str(ROOT / "data/v2/place_platform_v2.sqlite3"))
p.add_argument("--staging-root", default=str(ROOT / "data/v2/staging/user_web"))
p.add_argument("--commit", action="store_true", help="promote staged overlay JSON to public production JSON")
p.add_argument("--rollback", metavar="RELEASE_ID", help="restore V1 production JSON from a switch backup")
a = p.parse_args()

if a.rollback:
    result = rollback_production_switch(ROOT, a.rollback)
elif a.commit:
    result = commit_production_switch(ROOT, a.database, a.staging_root)
else:
    result = plan_production_switch(ROOT, a.database, a.staging_root)

print(json.dumps(result, ensure_ascii=False, indent=2))
if result.get("status") == "READY_TO_SWITCH":
    print("PRODUCTION_SWITCH = NOT_PERFORMED")
elif result.get("status") == "SWITCHED":
    print("PRODUCTION_SWITCH = PERFORMED")
    print("ROLLBACK = AVAILABLE")
elif result.get("status") == "ROLLED_BACK":
    print("PRODUCTION_SWITCH = ROLLED_BACK")
print("RESULT =", result.get("status"))
