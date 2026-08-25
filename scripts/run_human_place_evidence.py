from __future__ import annotations
import argparse, json
from pathlib import Path
from place_platform_v2.human_place_evidence import (
    apply_approved_coordinate_evidence, list_review_queue,
    review_coordinate_evidence, submit_coordinate_evidence,
)

p=argparse.ArgumentParser()
sub=p.add_subparsers(dest="cmd", required=True)
q=sub.add_parser("queue"); q.add_argument("--database",required=True); q.add_argument("--status",default="pending_review")
s=sub.add_parser("submit-coordinate"); s.add_argument("--database",required=True); s.add_argument("--place-id",required=True); s.add_argument("--latitude",required=True,type=float); s.add_argument("--longitude",required=True,type=float); s.add_argument("--source-kind",choices=["user","admin"],required=True); s.add_argument("--source-name",required=True); s.add_argument("--evidence-note",required=True); s.add_argument("--source-reference")
r=sub.add_parser("review"); r.add_argument("--database",required=True); r.add_argument("--submission-id",required=True); r.add_argument("--approve",action="store_true"); r.add_argument("--reject",action="store_true"); r.add_argument("--reviewer",required=True); r.add_argument("--review-note",required=True); r.add_argument("--review-basis"); r.add_argument("--coordinate-owner-confirmed",action="store_true")
a=sub.add_parser("apply"); a.add_argument("--database",required=True); a.add_argument("--submission-id",required=True); a.add_argument("--commit",action="store_true")
args=p.parse_args()
if args.cmd=="queue": out=list_review_queue(args.database,status=args.status)
elif args.cmd=="submit-coordinate": out=submit_coordinate_evidence(database_path=args.database,place_id=args.place_id,latitude=args.latitude,longitude=args.longitude,source_kind=args.source_kind,source_name=args.source_name,evidence_note=args.evidence_note,source_reference=args.source_reference)
elif args.cmd=="review":
    if args.approve==args.reject: raise SystemExit("choose exactly one of --approve/--reject")
    out=review_coordinate_evidence(database_path=args.database,submission_id=args.submission_id,approve=args.approve,reviewer=args.reviewer,review_note=args.review_note,review_basis=args.review_basis,coordinate_owner_confirmed=args.coordinate_owner_confirmed)
else: out=apply_approved_coordinate_evidence(database_path=args.database,submission_id=args.submission_id,commit=args.commit)
print(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))
