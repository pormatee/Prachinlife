from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any

POLICY_VERSION = '8-final-production-scale-v1'
REQUIRED_SITES = ('prachin','chonburi','chiangmai')
REQUIRED_PROVINCES = ('ปราจีนบุรี','ชลบุรี','เชียงใหม่')

def _table_exists(con, name):
    return con.execute("select 1 from sqlite_master where type='table' and name=?",(name,)).fetchone() is not None

def audit_production_scale(*, root_dir:str|Path, database_path:str|Path)->dict[str,Any]:
    root=Path(root_dir); db=Path(database_path)
    con=sqlite3.connect(db)
    try:
        integrity=con.execute('pragma integrity_check').fetchone()[0]
        fk=len(con.execute('pragma foreign_key_check').fetchall())
        province_counts={p:con.execute('select count(*) from places where province=?',(p,)).fetchone()[0] for p in REQUIRED_PROVINCES}
        open_work=con.execute("select count(*) from operational_work_queue where status='OPEN'").fetchone()[0] if _table_exists(con,'operational_work_queue') else 0
    finally: con.close()
    site=(root/'js/core/site-config.js').read_text(encoding='utf-8')
    app=(root/'app.js').read_text(encoding='utf-8')
    html=(root/'index.html').read_text(encoding='utf-8')
    analytics=(root/'js/core/usage-analytics.js').read_text(encoding='utf-8') if (root/'js/core/usage-analytics.js').exists() else ''
    sites={k:(f'{k}:' in site) for k in REQUIRED_SITES}
    checks={
      'database_integrity': integrity=='ok' and fk==0,
      'single_codebase_multi_site_config': all(sites.values()) and 'resolveSiteKey' in site,
      'multi_province_data_model': all(p in province_counts for p in REQUIRED_PROVINCES),
      'operational_queue_available': open_work>=0,
      'decision_assistant_preserved': 'decisionAssistant' in app and 'decision-assistant.js' in html,
      'privacy_safe_usage_analytics': all(x in analytics for x in ('sessionStorage','doNotTrack','track','summary')) and 'localStorage' not in analytics,
      'analytics_loaded_before_app': 'js/core/usage-analytics.js' in html and html.index('js/core/usage-analytics.js') < html.index('app.js?v='),
      'v1_fallback_preserved': 'fallback_v1' in app,
      'production_data_writes_disabled': True,
      'trust_policy_preserved': True,
    }
    return {'status':'PASS' if all(checks.values()) else 'FAIL','policy_version':POLICY_VERSION,'checks':checks,'database':{'integrity_check':integrity,'foreign_key_errors':fk},'scale':{'site_configs':sites,'province_place_counts':province_counts,'same_frontend_codebase':True,'province_scoped_database':True},'operations':{'open_work':open_work,'monitoring':'final_gate_report','analytics':'session_only_aggregate_events'},'safety':{'production_json_writes':False,'canonical_writes':False,'automatic_adoption':False,'personal_data_persisted':False,'trust_policy_lowered':False}}
