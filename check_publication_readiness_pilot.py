#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.publication_readiness import evaluate_pilot_readiness

p=argparse.ArgumentParser(description='PrachinLife Phase 2W.2 read-only publication readiness pilot')
p.add_argument('--place-id',required=True)
p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3')
a=p.parse_args()
before=Path(a.database).read_bytes()
r=evaluate_pilot_readiness(a.database,a.place_id)
after=Path(a.database).read_bytes()
out=asdict(r); out['mode']='READ_ONLY'; out['database_unchanged']=before==after; out['publication_performed']=False; out['user_web_switched']=False
print(json.dumps(out,ensure_ascii=False,indent=2))
print('CANONICAL_WRITES = DISABLED')
print('PUBLICATION = DISABLED')
print('USER_WEB_SWITCH = DISABLED')
print('RESULT = PHASE2W2_PASS')
