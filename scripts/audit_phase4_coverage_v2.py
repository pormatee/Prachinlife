#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from place_platform_v2.phase4_coverage_reaudit import audit_phase4_coverage
p=argparse.ArgumentParser();p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--reports-dir',default='data/v2/discovery_reports');p.add_argument('--output',default='data/v2/discovery_reports/phase4_19_coverage_reaudit_v2.json');p.add_argument('--province',default='ปราจีนบุรี');a=p.parse_args()
r=audit_phase4_coverage(database_path=a.database,reports_dir=a.reports_dir,province=a.province)
Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
