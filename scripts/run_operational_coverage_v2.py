#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.coverage_cycle_orchestrator import run_coverage_cycle
from place_platform_v2.operational_work_queue import sync_operational_work_queue
from place_platform_v2.phase5_operational_gate import evaluate_phase5_operational_gate
p=argparse.ArgumentParser(description='Run the PrachinLife V2 operational coverage machine')
p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--reports-dir',default='data/v2/discovery_reports');p.add_argument('--output',default='data/v2/discovery_reports/phase5_final_operational_cycle_v2.json');p.add_argument('--province',default='ปราจีนบุรี');p.add_argument('--category',default='vegetarian');p.add_argument('--commit-queue',action='store_true');p.add_argument('--commit-adoption',action='store_true')
a=p.parse_args()
cycle=run_coverage_cycle(root_dir=ROOT,database_path=a.database,reports_dir=a.reports_dir,province=a.province,category=a.category,commit_adoption=a.commit_adoption)
queue=sync_operational_work_queue(database_path=ROOT/a.database,work_items=cycle['work_items'],province=a.province,category=a.category,commit=a.commit_queue)
gate=evaluate_phase5_operational_gate(database_path=ROOT/a.database,cycle=cycle,queue=queue)
r={'status':gate['status'],'mode':{'queue':'COMMIT' if a.commit_queue else 'DRY_RUN','adoption':'CONTROLLED_COMMIT' if a.commit_adoption else 'DRY_RUN'},'scope':{'province':a.province,'category':a.category},'cycle':cycle,'work_queue':queue,'operator_summary':{'open_work':queue['open_queue_count'],'queue_counts':queue['queue_counts'],'ready_for_adoption':cycle['summary']['ready_for_adoption'],'coverage_work_remains':cycle['summary']['coverage_work_remains'],'discovery_continues':cycle['cycle']['discovery_continues']},'final_gate':gate}
out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STATUS =',r['status']);print('SCOPE =',a.province,'/',a.category);print('OPEN_WORK =',r['operator_summary']['open_work']);print('QUEUES =',r['operator_summary']['queue_counts']);print('READY_FOR_ADOPTION =',r['operator_summary']['ready_for_adoption']);print('DISCOVERY_CONTINUES =',r['operator_summary']['discovery_continues']);print('DATABASE_INTEGRITY =',gate['database']['integrity_check']);print('FOREIGN_KEY_ERRORS =',gate['database']['foreign_key_errors']);print('RESULT =',r['status']);print('REPORT =',out)
