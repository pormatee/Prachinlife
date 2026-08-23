#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.publication_impact_preview import preview_controlled_publication_impact

p=argparse.ArgumentParser(description='PrachinLife Phase 3.8 controlled publication impact preview')
p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3')
p.add_argument('--repo-root',default='.')
p.add_argument('--report',default='data/v2/discovery_reports/controlled_publication_impact_preview_v2.json')
a=p.parse_args()
r=preview_controlled_publication_impact(database_path=a.database,repo_root=a.repo_root)
out=Path(a.report); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
print('PRODUCTION_JSON_WRITES = DISABLED')
print('AUTOMATIC_PUBLICATION = DISABLED')
print('RESULT =', 'PUBLICATION_PREVIEW_PASS' if r['status']=='PASS' else 'PUBLICATION_PREVIEW_BLOCKED')
raise SystemExit(0 if r['status']=='PASS' else 2)
