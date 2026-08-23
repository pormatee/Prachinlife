#!/usr/bin/env python3
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.identity_evidence_followup import followup_identity_evidence
r=followup_identity_evidence(
 batch_report_path=ROOT/'data/v2/discovery_reports/coverage_batch2_v2.json',
 observations_path=ROOT/'data/v2/discovery_reports/phase4_17_identity_followup_observations.json',
 database_path=ROOT/'data/v2/place_platform_v2.sqlite3')
out=ROOT/'data/v2/discovery_reports/identity_evidence_followup_v2.json';out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
