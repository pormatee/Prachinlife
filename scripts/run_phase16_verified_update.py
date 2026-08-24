#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from place_platform_v2.phase16_verified_update import run_phase16
p=argparse.ArgumentParser()
p.add_argument("--database",default=str(ROOT/"data/v2/place_platform_v2.sqlite3"))
p.add_argument("--verified-updates",default=str(ROOT/"data/v2/phase16_verified_updates.json"))
p.add_argument("--commit",action="store_true")
a=p.parse_args()
print(json.dumps(run_phase16(repo_root=ROOT,database_path=a.database,verified_updates_path=a.verified_updates,commit=a.commit),ensure_ascii=False,indent=2))
