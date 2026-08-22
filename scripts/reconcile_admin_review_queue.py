#!/usr/bin/env python3
"""Repair stale pending admin draft versions without touching canonical data."""
from pathlib import Path
import argparse, sqlite3, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.admin_drafts import AdminDraftStore

def counts(path: Path):
    if not path.exists(): return {}
    con=sqlite3.connect(path)
    try:
        return dict(con.execute("SELECT status, COUNT(*) FROM admin_evidence_drafts GROUP BY status").fetchall())
    finally: con.close()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--draft-db',default=str(ROOT/'data/v2/admin_evidence_drafts.sqlite3')); args=ap.parse_args(); path=Path(args.draft_db)
    before=counts(path)
    with AdminDraftStore(path):
        pass
    after=counts(path)
    print('Before:', before)
    print('After :', after)
    print('Canonical writes: DISABLED')
    print('Publication: DISABLED')
    return 0
if __name__=='__main__': raise SystemExit(main())
