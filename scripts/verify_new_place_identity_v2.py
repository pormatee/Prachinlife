#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.new_place_identity_verification import verify_new_place_candidates
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--discovery-report",default="data/v2/discovery_reports/new_place_discovery_v2.json")
 p.add_argument("--evidence",default="data/v2/discovery_reports/phase4_3_identity_evidence_observations.json")
 p.add_argument("--output",default="data/v2/discovery_reports/new_place_identity_verification_v2.json")
 a=p.parse_args()
 d=json.loads((ROOT/a.discovery_report).read_text(encoding="utf-8"))
 e=json.loads((ROOT/a.evidence).read_text(encoding="utf-8"))
 r=verify_new_place_candidates(ROOT/a.database,d,e)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({k:r[k] for k in ("status","candidate_count","decision_counts","ready_for_precanonical_evidence_count","needs_more_evidence_count","safety")},ensure_ascii=False,indent=2))
 for x in r["decisions"]: print("DECISION =",x["name"],"|",x["identity_outcome"],"| sources =",x["independent_source_family_count"],"| next =",x["next_step"])
 print("REPORT =",out)
if __name__=="__main__":main()
