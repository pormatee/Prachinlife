#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from place_platform_v2.staged_milestone import select_pilot_queue,acquire_osm_queue,commit_current_observations,eligible_place_ids
from place_platform_v2.staged_overlay import build_overlay_staging
p=argparse.ArgumentParser();p.add_argument('--database',default='data/v2/place_platform_v2.sqlite3');p.add_argument('--province',default='ปราจีนบุรี');p.add_argument('--pilot-limit',type=int,default=20);p.add_argument('--acquire-osm',action='store_true');p.add_argument('--commit-observations',action='store_true');p.add_argument('--stage-export',action='store_true');a=p.parse_args()
q=select_pilot_queue(a.database,a.province,a.pilot_limit);r={'mode':'COMMIT_STAGING' if a.commit_observations else 'READ_ONLY','policy_version':'staged-milestone-v1','province':a.province,'pilot_count':len(q),'pilot_queue':q,'acquisition_performed':False,'canonical_fields_changed':False,'production_export_changed':False,'user_web_switched':False}
obs=[]
if a.acquire_osm:obs=acquire_osm_queue(q);r['observations']=obs;r['acquisition_performed']=True
if a.commit_observations:
 if not a.acquire_osm:raise SystemExit('--commit-observations requires --acquire-osm')
 backup=ROOT/'data/v2/backups'/('place_platform_v2.pre-staged-milestone.sqlite3');backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.database,backup);r['backup']=str(backup);r['committed_observations']=commit_current_observations(a.database,obs)
if a.stage_export:r['staging_manifest']=build_overlay_staging(a.database,ROOT,ROOT/'data/v2/staging/user_web',a.province)
elig,blocked=eligible_place_ids(a.database,a.province);r['eligible_count']=len(elig);r['blocked_count']=len(blocked)
print(json.dumps(r,ensure_ascii=False,indent=2));print('CANONICAL_FIELD_WRITES = DISABLED');print('PRODUCTION_EXPORT = UNCHANGED');print('PUBLIC_USER_WEB_SWITCH = DISABLED');print('PREVIEW = ?v2preview=1');print('RESULT = STAGED_MILESTONE_PASS')
