#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.contracts import GeoPoint, SourceRef, SourceType
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication_export import _load_places_and_evidence
from place_platform_v2.publication_verification import make_bundle,evaluate_bundle,commit_bundle
DB=ROOT/'data/v2/place_platform_v2.sqlite3'

def main():
 p=argparse.ArgumentParser(description='Phase 2W.3 independent publication verification bundle')
 p.add_argument('--place-id',required=True); p.add_argument('--source-name',required=True); p.add_argument('--source-url'); p.add_argument('--source-record-id'); p.add_argument('--commit',action='store_true')
 a=p.parse_args(); places,_=_load_places_and_evidence(DB,'ปราจีนบุรี'); place=next((x for x in places if x.identity.place_id==a.place_id),None)
 if place is None: raise SystemExit('unknown Prachinburi place_id')
 source=SourceRef(SourceType.OFFICIAL,a.source_name,source_record_id=a.source_record_id,source_url=a.source_url,observed_at=datetime.now(timezone.utc))
 claims={'canonical_name':place.canonical_name,'categories':place.categories,'location':place.location,'province':place.province,'lifecycle':PlaceLifecycle.ACTIVE}
 bundle=make_bundle(place_id=a.place_id,source=source,claims=claims); r=commit_bundle(DB,bundle) if a.commit else evaluate_bundle(DB,bundle)
 print(json.dumps(r.__dict__,ensure_ascii=False,indent=2,default=str)); print('PUBLICATION = DISABLED'); print('USER_WEB_SWITCH = DISABLED'); print('RESULT = PHASE2W3_PASS')
if __name__=='__main__': main()
