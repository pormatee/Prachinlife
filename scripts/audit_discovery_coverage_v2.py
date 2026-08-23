#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.discovery_coverage_audit import audit_discovery_coverage
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
    ap.add_argument("--output",default="data/v2/discovery_reports/discovery_coverage_audit_v2.json")
    ap.add_argument("--priority-limit",type=int,default=50)
    ap.add_argument("--focus-province",default="ปราจีนบุรี")
    a=ap.parse_args()
    r=audit_discovery_coverage(ROOT/a.database,a.priority_limit,a.focus_province or None)
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False,indent=2))
    print("REPORT =",out)
if __name__=="__main__": main()
