#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.coverage_cycle_orchestrator import run_coverage_cycle
from place_platform_v2.operational_work_queue import sync_operational_work_queue
from place_platform_v2.phase6_data_expansion import audit_prachinburi_data_quality,build_expansion_work
from place_platform_v2.phase6_final_gate import evaluate_phase6_final_gate
p=argparse.ArgumentParser();p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--reports-dir',default='data/v2/discovery_reports');p.add_argument('--output',default='data/v2/discovery_reports/phase6_final_data_expansion_v2.json');p.add_argument('--province',default='ปราจีนบุรี');p.add_argument('--commit-queue',action='store_true');a=p.parse_args()
db=ROOT/a.database;rd=ROOT/a.reports_dir
audit=audit_prachinburi_data_quality(database_path=db,province=a.province)
legacy=run_coverage_cycle(root_dir=ROOT,database_path=a.database,reports_dir=a.reports_dir,province=a.province,category='vegetarian',commit_adoption=False)
work=build_expansion_work(audit=audit,existing_cycle=legacy)
# Phase 6 uses one queue scope so category-level work can coexist and deduplicate across all categories.
queue=sync_operational_work_queue(database_path=db,work_items=work,province=a.province,category='all',commit=a.commit_queue)
report={'status':'PASS','policy_version':'6-final-operational-expansion-v1','scope':{'province':a.province,'category':'all'},'quality_audit':audit,'work_items':work,'work_queue':queue,'summary':{'canonical_places':audit['canonical_place_count'],'categories_accounted':len(audit['categories']),'category_work_items':sum(1 for x in work if x.get('candidate_id') is None),'concrete_candidate_work':sum(1 for x in work if x.get('candidate_id') is not None),'open_work':queue['open_queue_count'],'queue_counts':queue['queue_counts'],'coverage_work_remains':True,'discovery_continues':True},'safety':{'canonical_writes':False,'precanonical_writes':False,'production_json_writes':False,'automatic_adoption':False,'explicit_adoption_commit_required':True,'trust_policy_lowered':False}}
report['final_gate']=evaluate_phase6_final_gate(database_path=db,report=report,queue=queue);report['status']=report['final_gate']['status']
out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STATUS =',report['status']);print('CANONICAL_PLACES =',report['summary']['canonical_places']);print('CATEGORIES_ACCOUNTED =',report['summary']['categories_accounted']);print('CATEGORY_WORK_ITEMS =',report['summary']['category_work_items']);print('OPEN_WORK =',report['summary']['open_work']);print('QUEUES =',report['summary']['queue_counts']);print('DISCOVERY_CONTINUES =',report['summary']['discovery_continues']);print('DATABASE_INTEGRITY =',report['final_gate']['database']['integrity_check']);print('FOREIGN_KEY_ERRORS =',report['final_gate']['database']['foreign_key_errors']);print('RESULT =',report['status']);print('REPORT =',out)
