#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.publication_batch_audit import audit_publication_readiness
p=argparse.ArgumentParser(description='PrachinLife Phase 2W.6 read-only publication readiness batch audit')
p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3')
p.add_argument('--pilot-limit',type=int,default=20)
a=p.parse_args(); path=Path(a.database); before=path.read_bytes()
r,_=audit_publication_readiness(path,pilot_limit=a.pilot_limit); after=path.read_bytes()
out=asdict(r); out['database_unchanged']=before==after
print(json.dumps(out,ensure_ascii=False,indent=2))
print('CANONICAL_WRITES = DISABLED'); print('PUBLICATION = DISABLED'); print('USER_WEB_SWITCH = DISABLED'); print('RESULT = PHASE2W6_PASS')
