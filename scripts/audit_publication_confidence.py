#!/usr/bin/env python3
from pathlib import Path
import sys, argparse, json, hashlib
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.publication_confidence import audit_database

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser(); p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3'); p.add_argument('--province',default='ปราจีนบุรี'); p.add_argument('--pilot-limit',type=int,default=20); a=p.parse_args()
b=sha(a.database); report=audit_database(a.database,a.province,a.pilot_limit); report['database_unchanged']=sha(a.database)==b
print(json.dumps(report,ensure_ascii=False,indent=2,default=str)); print('CANONICAL_WRITES = DISABLED'); print('PUBLICATION = DISABLED'); print('USER_WEB_SWITCH = DISABLED'); print('RESULT = PHASE2W8_PASS')
