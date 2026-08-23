#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from place_platform_v2.post_publication_verification import verify_post_publication

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--output", default="data/v2/discovery_reports/post_publication_verification_v2.json")
    args=ap.parse_args()
    root=Path(args.repo_root).resolve()
    result=verify_post_publication(root)
    out=root/args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"REPORT = {out}")
    raise SystemExit(0 if result["status"]=="PASS" else 2)

if __name__=="__main__":
    main()
