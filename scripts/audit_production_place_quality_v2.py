from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.production_quality import audit_production
FILES=("prachinlife_index.json","vegetarian_index.json","go_index.json","service_index.json")

def digest(p: Path)->str:
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=ROOT); ap.add_argument('--json',type=Path,default=Path('data/v2/discovery_reports/production_place_quality_v2.json')); args=ap.parse_args()
 paths=[args.root/f for f in FILES]; before={f.name:digest(f) for f in paths}
 datasets={f.name:json.loads(f.read_text(encoding='utf-8')) for f in paths}
 report=audit_production(datasets); report['input_sha256']=before
 out=args.root/args.json if not args.json.is_absolute() else args.json; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 after={f.name:digest(f) for f in paths}
 if before!=after: raise SystemExit('FAIL: production input changed during read-only audit')
 print(f"VISIBLE_PLACES={report['visible_place_count']}"); print('QUALITY='+json.dumps(report['quality_tiers'],sort_keys=True)); print('ACTION_READY='+json.dumps(report['action_ready'],sort_keys=True)); print('MISSING='+json.dumps(report['missing_fields'],sort_keys=True)); print('RESULT=PASS')
if __name__=='__main__': main()
