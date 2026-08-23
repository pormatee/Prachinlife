#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.direct_lifecycle_confirmation import evaluate_direct_confirmation
def main():
 p=argparse.ArgumentParser();p.add_argument("--commit",action="store_true")
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--confirmation",default="data/v2/discovery_reports/phase4_7_direct_confirmation.json")
 p.add_argument("--output",default="data/v2/discovery_reports/direct_lifecycle_confirmation_v2.json")
 a=p.parse_args()
 r=evaluate_direct_confirmation(database_path=ROOT/a.database,confirmation_path=ROOT/a.confirmation,commit=a.commit)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(r,ensure_ascii=False,indent=2));print("REPORT =",out)
if __name__=="__main__":main()
