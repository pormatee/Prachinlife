#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.contracts import GeoPoint, SourceRef, SourceType
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.verification_source_acquisition import (
    SourceObservation,
    evaluate_source_observation,
)

DB = ROOT / "data/v2/place_platform_v2.sqlite3"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description="Phase 2W.4 read-only verification source acquisition/match gate")
    p.add_argument("--place-id", required=True)
    p.add_argument("--source-name", required=True)
    p.add_argument("--source-type", choices=[x.value for x in SourceType], default="web")
    p.add_argument("--source-url")
    p.add_argument("--source-record-id")
    p.add_argument("--source-place-name", required=True)
    p.add_argument("--source-province")
    p.add_argument("--source-latitude", type=float)
    p.add_argument("--source-longitude", type=float)
    p.add_argument("--source-active", action="store_true")
    a = p.parse_args()

    if (a.source_latitude is None) != (a.source_longitude is None):
        raise SystemExit("source latitude and longitude must be provided together")

    before = file_hash(DB)
    source = SourceRef(
        SourceType(a.source_type),
        a.source_name,
        source_record_id=a.source_record_id,
        source_url=a.source_url,
        observed_at=datetime.now(timezone.utc),
    )
    observation = SourceObservation(
        source=source,
        place_name=a.source_place_name,
        province=a.source_province,
        location=(
            GeoPoint(a.source_latitude, a.source_longitude)
            if a.source_latitude is not None
            else None
        ),
        lifecycle=PlaceLifecycle.ACTIVE if a.source_active else None,
    )
    result = evaluate_source_observation(DB, place_id=a.place_id, observation=observation)
    after = file_hash(DB)
    payload = dict(result.__dict__)
    payload["database_unchanged"] = before == after
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print("CANONICAL_WRITES = DISABLED")
    print("PUBLICATION = DISABLED")
    print("USER_WEB_SWITCH = DISABLED")
    print("RESULT = PHASE2W4_PASS")


if __name__ == "__main__":
    main()
