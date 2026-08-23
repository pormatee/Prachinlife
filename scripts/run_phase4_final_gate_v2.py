#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from place_platform_v2.phase4_final_gate import run_phase4_final_gate
p=argparse.ArgumentParser();p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--reports-dir',default='data/v2/discovery_reports');p.add_argument('--output',default='data/v2/discovery_reports/phase4_20_final_gate_v2.json');a=p.parse_args()
r=run_phase4_final_gate(database_path=a.database,reports_dir=a.reports_dir)
Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['status']=='PASS' else 1)
