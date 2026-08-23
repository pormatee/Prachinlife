#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from place_platform_v2.coverage_cycle_orchestrator import run_coverage_cycle

p=argparse.ArgumentParser(description='Run one V2 coverage-machine operational cycle')
p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3')
p.add_argument('--reports-dir',default='data/v2/discovery_reports')
p.add_argument('--output',default='data/v2/discovery_reports/phase5_1_coverage_cycle_v2.json')
p.add_argument('--province',default='ปราจีนบุรี')
p.add_argument('--category',default='vegetarian')
p.add_argument('--commit-adoption',action='store_true',help='explicitly allow the existing controlled adoption machine to commit READY candidates')
a=p.parse_args()
r=run_coverage_cycle(root_dir=ROOT,database_path=a.database,reports_dir=a.reports_dir,province=a.province,category=a.category,commit_adoption=a.commit_adoption)
out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2));print('REPORT =',out)
