#!/usr/bin/env python
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.core_place_verification_compat import evaluate_compatibility
p=argparse.ArgumentParser();p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--coordinate-report',action='append',default=[]);p.add_argument('--output',default='data/v2/discovery_reports/core_place_verification_v2_compat_v1.json');a=p.parse_args()
r=evaluate_compatibility(database_path=ROOT/a.database,coordinate_report_paths=[ROOT/x for x in a.coordinate_report]);out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=False,indent=2))
