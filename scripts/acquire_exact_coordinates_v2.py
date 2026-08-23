#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.exact_coordinate_acquisition import acquire_exact_coordinates
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--geolocation-report",default="data/v2/discovery_reports/geolocation_precanonical_v2.json")
 p.add_argument("--observations",default="data/v2/discovery_reports/phase4_12_exact_coordinate_observations.json")
 p.add_argument("--output",default="data/v2/discovery_reports/exact_coordinate_acquisition_v2.json")
 a=p.parse_args()
 r=acquire_exact_coordinates(database_path=ROOT/a.database,geolocation_report_path=ROOT/a.geolocation_report,observations_path=ROOT/a.observations)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(r,ensure_ascii=False,indent=2));print("REPORT =",out)
if __name__=="__main__":main()
