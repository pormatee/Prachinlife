#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.targeted_enrichment import build_targeted_enrichment_plan


def main():
    ap=argparse.ArgumentParser(description='Build read-only Phase 3.2 targeted enrichment acquisition plan')
    ap.add_argument('--db', default=str(ROOT/'data/v2/place_platform_v2.sqlite3'))
    ap.add_argument('--quality-report', default=str(ROOT/'data/v2/discovery_reports/production_place_quality_v2.json'))
    ap.add_argument('--output', default=str(ROOT/'data/v2/discovery_reports/targeted_production_enrichment_v2.json'))
    ap.add_argument('--limit', type=int, default=50)
    args=ap.parse_args()
    report=build_targeted_enrichment_plan(database_path=args.db, repo_root=ROOT, quality_report_path=args.quality_report, limit=args.limit)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('QUEUE_COUNT=', report['queue_count'])
    print('MAPPED_VISIBLE=', report['mapped_visible_place_count'])
    print('UNMAPPED_PRIORITY=', report['unmapped_priority_count'])
    print('NEXT_STEPS=', json.dumps(report['next_step_counts'],ensure_ascii=False,sort_keys=True))
    print('DATABASE_UNCHANGED=', report['safety']['database_unchanged'])
    print('RESULT=PASS' if report['queue_count']==args.limit and report['unmapped_priority_count']==0 and report['safety']['database_unchanged'] else 'RESULT=REVIEW')

if __name__=='__main__': main()
