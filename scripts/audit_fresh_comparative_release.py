#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.comparative_release_gate import audit_fresh_comparative_release
r=audit_fresh_comparative_release(ROOT,ROOT/'data/v2/place_platform_v2.sqlite3',ROOT/'data/v2/staging/user_web')
out=ROOT/'data/v2/discovery_reports/fresh_comparative_release_gate.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
print('COMPARATIVE_VALIDATION =',r['status'])
print('ROLLBACK =','VERIFIED' if r['rollback_verified'] else 'FAILED')
print('PRODUCTION_SWITCH = DISABLED')
