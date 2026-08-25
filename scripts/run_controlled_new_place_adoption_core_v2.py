#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.controlled_new_place_adoption_core_v2 import (
    run_controlled_new_place_adoption_core_v2,
)

p = argparse.ArgumentParser()
p.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
p.add_argument("--coordinate-report", action="append", default=[])
p.add_argument("--commit", action="store_true")
p.add_argument(
    "--output",
    default="data/v2/discovery_reports/controlled_new_place_adoption_core_v2.json",
)
a = p.parse_args()

reports = [ROOT / x for x in a.coordinate_report]
r = run_controlled_new_place_adoption_core_v2(
    database_path=ROOT / a.database,
    coordinate_report_paths=reports,
    commit=a.commit,
)

out = ROOT / a.output
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(r, ensure_ascii=False, indent=2))
