#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.continued_discovery_batch import continue_discovery_batch
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--observations",default="data/v2/discovery_reports/phase4_9_batch_observations.json")
 p.add_argument("--prior-discovery",default="data/v2/discovery_reports/new_place_discovery_v2.json")
 p.add_argument("--output",default="data/v2/discovery_reports/continued_discovery_batch_v2.json")
 a=p.parse_args()
 r=continue_discovery_batch(database_path=ROOT/a.database,observations_path=ROOT/a.observations,
                            prior_discovery_report_path=ROOT/a.prior_discovery)
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({k:r[k] for k in ("status","source_observation_count","candidate_group_count","batch_state_counts",
 "new_candidate_count","verification_queue_count","pending_queue_count","discovery_continues","safety")},ensure_ascii=False,indent=2))
 for x in r["batch_results"]:
  print("BATCH =",x["name"],"|",x["batch_state"],"| sources =",x["independent_source_family_count"],"| next =",x["next_step"])
 print("REPORT =",out)
if __name__=="__main__":main()
