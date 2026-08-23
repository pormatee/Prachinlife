#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from place_platform_v2.pending_coordinate_queue import queue_pending_coordinates

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--commit", action="store_true")
    p.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
    p.add_argument("--direct-coordinate-report", default="data/v2/discovery_reports/direct_coordinate_confirmation_v2.json")
    p.add_argument("--output", default="data/v2/discovery_reports/pending_coordinate_queue_v2.json")
    a = p.parse_args()
    r = queue_pending_coordinates(database_path=ROOT/a.database,
                                  direct_coordinate_report_path=ROOT/a.direct_coordinate_report,
                                  commit=a.commit)
    out = ROOT/a.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print("REPORT =", out)

if __name__ == "__main__":
    main()
