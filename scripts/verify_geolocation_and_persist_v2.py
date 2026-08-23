#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.geolocation_precanonical import verify_geolocation_and_persist
def main():
 p=argparse.ArgumentParser();p.add_argument("--commit",action="store_true")
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--identity-report",default="data/v2/discovery_reports/batch_identity_verification_v2.json")
 p.add_argument("--identity-evidence",default="data/v2/discovery_reports/phase4_10_batch_identity_evidence.json")
 p.add_argument("--geo-evidence",default="data/v2/discovery_reports/phase4_11_geolocation_observations.json")
 p.add_argument("--output",default="data/v2/discovery_reports/geolocation_precanonical_v2.json")
 a=p.parse_args()
 r=verify_geolocation_and_persist(database_path=ROOT/a.database,identity_report_path=ROOT/a.identity_report,
 identity_evidence_path=ROOT/a.identity_evidence,geolocation_observations_path=ROOT/a.geo_evidence,commit=a.commit)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(r,ensure_ascii=False,indent=2));print("REPORT =",out)
if __name__=="__main__":main()
