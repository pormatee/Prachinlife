#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.coverage_batch2 import continue_coverage_batch2
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--observations",default="data/v2/discovery_reports/phase4_15_coverage_batch2_observations.json")
 p.add_argument("--prior-batch",default="data/v2/discovery_reports/continued_discovery_batch_v2.json")
 p.add_argument("--prior-identity",default="data/v2/discovery_reports/batch_identity_verification_v2.json")
 p.add_argument("--output",default="data/v2/discovery_reports/coverage_batch2_v2.json")
 a=p.parse_args()
 r=continue_coverage_batch2(database_path=ROOT/a.database,observations_path=ROOT/a.observations,
 prior_batch_path=ROOT/a.prior_batch,prior_identity_report_path=ROOT/a.prior_identity)
 out=ROOT/a.output;out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({k:r[k] for k in ("status","source_observation_count","candidate_group_count","batch_state_counts",
 "new_candidate_count","followup_queue_count","pending_candidate_count","discovery_continues","quality","safety")},ensure_ascii=False,indent=2))
 for x in r["results"]:
  print("CANDIDATE =",x["name"],"|",x["batch_state"],"| dedicated =",x["dedicated_diet_signal"],"| next =",x["next_step"])
 print("REPORT =",out)
if __name__=="__main__":main()
