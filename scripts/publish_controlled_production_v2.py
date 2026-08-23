#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from place_platform_v2.controlled_production_publication import plan_controlled_production_publication,commit_controlled_production_publication,rollback_controlled_production_publication
p=argparse.ArgumentParser(); p.add_argument("--database",default=str(ROOT/"data/v2/place_platform_v2.sqlite3")); p.add_argument("--commit",action="store_true"); p.add_argument("--rollback")
a=p.parse_args()
if a.rollback: r=rollback_controlled_production_publication(repo_root=ROOT,release_id=a.rollback)
elif a.commit: r=commit_controlled_production_publication(repo_root=ROOT,database_path=a.database)
else: r=plan_controlled_production_publication(repo_root=ROOT,database_path=a.database)
print(json.dumps(r,ensure_ascii=False,indent=2)); print("RESULT =",r["status"])
