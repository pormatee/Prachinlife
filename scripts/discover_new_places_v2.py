#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.new_place_discovery import build_osm_vegetarian_query,discover_new_vegetarian_candidates
from place_platform_v2.osm_live import fetch_overpass
def main():
 p=argparse.ArgumentParser();p.add_argument("--database",default="data/v2/place_platform_v2.sqlite3")
 p.add_argument("--province",default="ปราจีนบุรี");p.add_argument("--iso3166-2",default="TH-25")
 p.add_argument("--observations");p.add_argument("--output",default="data/v2/discovery_reports/new_place_discovery_v2.json")
 a=p.parse_args()
 if a.observations:
  elements=json.loads((ROOT/a.observations).read_text(encoding="utf-8"))
  if isinstance(elements,dict):elements=elements.get("elements",[])
  source="fixture"
 else:
  f=fetch_overpass(build_osm_vegetarian_query(a.iso3166_2));elements=list(f.elements);source=f.endpoint
 r=discover_new_vegetarian_candidates(ROOT/a.database,elements,a.province);r["acquisition_source"]=source
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({k:r[k] for k in ("status","province","source_observation_count","new_place_candidate_count","existing_place_match_count","review_count","candidate_only","safety")},ensure_ascii=False,indent=2))
 print("REPORT =",out)
if __name__=="__main__":main()
