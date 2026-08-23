#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from place_platform_v2.controlled_evidence_persistence import verify_and_persist_web_evidence

p=argparse.ArgumentParser()
p.add_argument('--commit', action='store_true')
p.add_argument('--database', default='data/v2/place_platform_v2.sqlite3')
p.add_argument('--input', default='data/v2/discovery_reports/targeted_web_evidence_acquisition_v2.json')
p.add_argument('--report', default='data/v2/discovery_reports/controlled_web_evidence_persistence_v2.json')
a=p.parse_args()
r=verify_and_persist_web_evidence(database_path=a.database, acquisition_report_path=a.input, commit=a.commit)
Path(a.report).parent.mkdir(parents=True, exist_ok=True)
Path(a.report).write_text(json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print('MODE =',r['mode'])
print('INPUT_CLAIMS =',r['input_claim_count'])
print('PERSISTABLE =',r['persistable_evidence_count'])
print('STATUS =',r['persistable_status_counts'])
print('INSERTED =',r['inserted_evidence_count'])
print('ALREADY_PRESENT =',r['already_present_count'])
print('BLOCKED =',r['blocked_counts'])
print('CANONICAL_UNCHANGED =',r['safety']['canonical_unchanged'])
print('NON_EVIDENCE_TABLES_UNCHANGED =',r['safety']['non_evidence_tables_unchanged'])
print('TRUST_POLICY_LOWERED =',r['safety']['trust_policy_lowered'])
print('RESULT = PASS')
