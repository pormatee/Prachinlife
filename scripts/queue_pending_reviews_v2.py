#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.pending_review_queue import queue_pending_reviews
p=argparse.ArgumentParser(); p.add_argument('--commit',action='store_true'); p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3'); p.add_argument('--output',default='data/v2/discovery_reports/pending_review_queue_v2.json'); a=p.parse_args()
r=queue_pending_reviews(database_path=ROOT/a.database,adoption_report_path=ROOT/'data/v2/discovery_reports/new_place_adoption_review_v2.json',lifecycle_report_path=ROOT/'data/v2/discovery_reports/lifecycle_conflict_resolution_v2.json',direct_confirmation_report_path=ROOT/'data/v2/discovery_reports/direct_lifecycle_confirmation_v2.json',coverage_report_path=ROOT/'data/v2/discovery_reports/discovery_coverage_audit_v2.json',commit=a.commit)
out=ROOT/a.output; out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(r,ensure_ascii=False,indent=2)); print('REPORT =',out)
