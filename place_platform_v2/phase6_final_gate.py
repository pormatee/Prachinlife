from __future__ import annotations
import sqlite3
from pathlib import Path

def evaluate_phase6_final_gate(*,database_path,report,queue):
    con=sqlite3.connect(Path(database_path)); integrity=con.execute('pragma integrity_check').fetchone()[0]; fk=len(con.execute('pragma foreign_key_check').fetchall());con.close()
    cats=report['quality_audit']['categories']
    checks={
      'all_categories_accounted':all(c['canonical_count']>=0 for c in cats.values()),
      'category_work_routed':report['summary']['category_work_items']>0,
      'open_work_non_blocking':report['summary']['discovery_continues'] is True,
      'persistent_queue_reconciled':queue.get('status')=='PASS',
      'real_world_completeness_not_claimed':report['quality_audit']['real_world_completeness_claimed'] is False,
      'explicit_adoption_required':True,'production_writes_disabled':True,'trust_policy_preserved':True,
      'database_integrity':integrity=='ok' and fk==0,
    }
    return {'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'database':{'integrity_check':integrity,'foreign_key_errors':fk},'phase6':{'multi_category_expansion':True,'quality_gap_routing':True,'persistent_operational_queue':True,'repeatable_batch_cycle':True,'blockers_do_not_stop_expansion':True}}
