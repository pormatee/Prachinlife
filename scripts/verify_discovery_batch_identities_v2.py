#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.batch_identity_verification import verify_batch_identities
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--batch-report",default="data/v2/discovery_reports/continued_discovery_batch_v2.json")
 p.add_argument("--evidence",default="data/v2/discovery_reports/phase4_10_batch_identity_evidence.json")
 p.add_argument("--output",default="data/v2/discovery_reports/batch_identity_verification_v2.json")
 a=p.parse_args()
 r=verify_batch_identities(database_path=ROOT/a.database,batch_report_path=ROOT/a.batch_report,evidence_path=ROOT/a.evidence)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({k:r[k] for k in ("status","verification_queue_count","decision_counts","verified_identity_count",
 "supported_identity_count","ready_for_geolocation_count","needs_more_identity_evidence_count","safety")},ensure_ascii=False,indent=2))
 for x in r["decisions"]: print("VERIFY =",x["name"],"|",x["identity_outcome"],"| sources =",x["independent_source_family_count"],"| next =",x["next_step"])
 print("REPORT =",out)
if __name__=="__main__":main()
