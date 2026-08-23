#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.precanonical_evidence_persistence import persist_verified_precanonical_evidence
def main():
 p=argparse.ArgumentParser();p.add_argument("--commit",action="store_true")
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--verification-report",default="data/v2/discovery_reports/new_place_identity_verification_v2.json")
 p.add_argument("--evidence",default="data/v2/discovery_reports/phase4_3_identity_evidence_observations.json")
 p.add_argument("--output",default="data/v2/discovery_reports/precanonical_evidence_persistence_v2.json")
 a=p.parse_args()
 r=persist_verified_precanonical_evidence(database_path=ROOT/a.database,
   verification_report_path=ROOT/a.verification_report,evidence_observations_path=ROOT/a.evidence,commit=a.commit)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(r,ensure_ascii=False,indent=2));print("REPORT =",out)
if __name__=="__main__":main()
