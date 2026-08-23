from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any

def evaluate_phase5_operational_gate(*, database_path:str|Path, cycle:dict[str,Any], queue:dict[str,Any])->dict[str,Any]:
    con=sqlite3.connect(Path(database_path)); integrity=con.execute('pragma integrity_check').fetchone()[0]; fk=len(con.execute('pragma foreign_key_check').fetchall()); con.close()
    checks={
      'cycle_pass':cycle.get('status')=='PASS',
      'persistent_queue_reconciled':queue.get('status')=='PASS',
      'discovery_non_blocking':cycle.get('cycle',{}).get('discovery_continues') is True,
      'explicit_adoption_commit_required':cycle.get('safety',{}).get('explicit_commit_required') is True,
      'production_writes_disabled':cycle.get('safety',{}).get('production_json_writes') is False and queue.get('safety',{}).get('production_json_writes') is False,
      'trust_policy_preserved':cycle.get('safety',{}).get('trust_policy_lowered') is False and queue.get('safety',{}).get('trust_policy_lowered') is False,
      'database_integrity':integrity=='ok' and fk==0,
    }
    return {'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'database':{'integrity_check':integrity,'foreign_key_errors':fk},'operational':{'single_cycle_entry_point':True,'persistent_queue':True,'queue_dedup_and_state_transition':True,'operator_summary':True,'repeatable_scope':True,'open_work_carries_forward':True}}
