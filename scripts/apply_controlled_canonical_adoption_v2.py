#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from place_platform_v2.controlled_canonical_adoption import apply_controlled_canonical_adoption
p=argparse.ArgumentParser(); p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3'); p.add_argument('--commit',action='store_true'); p.add_argument('--report',default='data/v2/discovery_reports/controlled_canonical_adoption_apply_v2.json'); a=p.parse_args()
r=apply_controlled_canonical_adoption(database_path=a.database,commit=a.commit)
Path(a.report).parent.mkdir(parents=True,exist_ok=True); Path(a.report).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('mode','proposal_count','apply_outcome_counts','updated_field_count','inserted_revision_count','already_applied_count')},ensure_ascii=False,indent=2)); print('safety =',r['safety'])
