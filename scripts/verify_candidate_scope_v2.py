#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.candidate_scope_verification import verify_candidate_scope

def main():
 p=argparse.ArgumentParser();p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--coverage-report',default='data/v2/discovery_reports/coverage_batch2_v2.json');p.add_argument('--observations',default='data/v2/discovery_reports/phase4_16_scope_observations.json');p.add_argument('--output',default='data/v2/discovery_reports/candidate_scope_verification_v2.json');a=p.parse_args()
 r=verify_candidate_scope(database_path=ROOT/a.database,coverage_report_path=ROOT/a.coverage_report,scope_observations_path=ROOT/a.observations);out=ROOT/a.output;out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:r[k] for k in ('status','scope_queue_count','decision_counts','dedicated_scope_verified_count','general_or_mixed_scope_count','scope_unresolved_count','primary_directory_ready_count','quality','safety')},ensure_ascii=False,indent=2))
 for x in r['decisions']: print('PLACE =',x['name'],'| OUTCOME =',x['scope_outcome'],'| PRIMARY_READY =',x['primary_directory_ready'],'| NEXT =',x['next_step'])
 print('REPORT =',out)
if __name__=='__main__': main()
