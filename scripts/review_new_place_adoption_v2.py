#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.new_place_adoption_review import review_new_place_adoption
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--output",default="data/v2/discovery_reports/new_place_adoption_review_v2.json")
 a=p.parse_args()
 r=review_new_place_adoption(database_path=ROOT/a.database)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(r,ensure_ascii=False,indent=2));print("REPORT =",out)
if __name__=="__main__":main()
