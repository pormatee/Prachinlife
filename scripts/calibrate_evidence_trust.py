#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.evidence_trust_calibration import calibrate_evidence_trust,database_sha256,report_as_dict

def main():
    ap=argparse.ArgumentParser(description='PrachinLife Phase 2W.7 read-only evidence trust calibration')
    ap.add_argument('--database',default='data/v2/place_platform_v2.sqlite3')
    ap.add_argument('--province',default='ปราจีนบุรี')
    ap.add_argument('--pilot-limit',type=int,default=20)
    a=ap.parse_args(); before=database_sha256(a.database)
    report,_=calibrate_evidence_trust(a.database,province=a.province,pilot_limit=a.pilot_limit)
    after=database_sha256(a.database); payload=report_as_dict(report); payload['database_unchanged']=before==after
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    print('CANONICAL_WRITES = DISABLED'); print('PUBLICATION = DISABLED'); print('USER_WEB_SWITCH = DISABLED')
    print('RESULT = PHASE2W7_PASS' if before==after else 'RESULT = PHASE2W7_FAIL')
    return 0 if before==after else 2
if __name__=='__main__': raise SystemExit(main())
