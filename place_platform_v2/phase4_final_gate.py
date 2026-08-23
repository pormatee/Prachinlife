from __future__ import annotations
import hashlib, json, sqlite3
from pathlib import Path
from typing import Any

POLICY_VERSION = '4.20-phase4-final-gate-v1'
REQUIRED_PHASES = (15,16,17,18,19)

def _sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def _checkpoint(path: Path) -> dict[str,str]:
    out={}
    for line in path.read_text(encoding='utf-8').splitlines():
        if ' = ' in line:
            k,v=line.split(' = ',1); out[k.strip()]=v.strip()
    return out

def run_phase4_final_gate(*, root_dir: str|Path='.', database_path: str|Path='data/v2/place_platform_v2.sqlite3', reports_dir: str|Path='data/v2/discovery_reports') -> dict[str,Any]:
    root=Path(root_dir); db=root/Path(database_path); rd=root/Path(reports_dir); before=_sha(db)
    checkpoints={str(n):_checkpoint(root/f'PHASE4_{n}_CHECKPOINT.txt') for n in REQUIRED_PHASES}
    phase_pass={n:checkpoints[str(n)].get('STATUS')=='PASS' for n in REQUIRED_PHASES}
    reaudit=json.loads((rd/'phase4_19_coverage_reaudit_v2.json').read_text(encoding='utf-8'))
    adoption=json.loads((rd/'controlled_new_place_adoption_machine_v2.json').read_text(encoding='utf-8'))
    con=sqlite3.connect(f'{db.resolve().as_uri()}?mode=ro', uri=True)
    try:
        integrity=con.execute('pragma integrity_check').fetchone()[0]
        foreign_keys=list(con.execute('pragma foreign_key_check'))
        canonical=con.execute('select count(*) from places').fetchone()[0]
        precanonical=con.execute('select count(*) from precanonical_candidates').fetchone()[0]
        pending=con.execute('select count(*) from precanonical_pending_review').fetchone()[0]
    finally: con.close()
    acceptance={
      'required_checkpoints_pass': all(phase_pass.values()),
      'coverage_reaudit_pass': reaudit.get('status')=='PASS',
      'pending_does_not_block_discovery': reaudit['closure_assessment']['pending_does_not_block_discovery'] is True,
      'no_real_world_completeness_claim': reaudit['closure_assessment']['real_world_completeness_claimed'] is False,
      'coverage_work_explicitly_remains': reaudit['closure_assessment']['coverage_work_remains'] is True,
      'final_gate_ready_from_reaudit': reaudit['closure_assessment']['phase4_final_gate_ready'] is True,
      'controlled_adoption_requires_full_eligibility': adoption['safety']['commit_requires_full_eligibility'] is True,
      'no_ready_candidate_stranded': adoption.get('ready_count', adoption.get('eligible_count', 0))==0,
      'database_integrity_ok': integrity=='ok' and not foreign_keys,
    }
    after=_sha(db)
    safety={'database_unchanged':before==after,'database_writes':False,'canonical_writes':False,'precanonical_writes':False,'pending_writes':False,'production_json_writes':False,'automatic_publication':False,'trust_policy_lowered':False,'read_only_gate':True}
    passed=all(acceptance.values()) and safety['database_unchanged']
    return {'status':'PASS' if passed else 'BLOCKED','policy_version':POLICY_VERSION,'required_phases':list(REQUIRED_PHASES),'phase_checkpoint_pass':{str(k):v for k,v in phase_pass.items()},'acceptance':acceptance,'database':{'integrity_check':integrity,'foreign_key_errors':len(foreign_keys),'canonical_places':canonical,'precanonical_candidates':precanonical,'pending_reviews':pending},'coverage_snapshot':{'canonical_primary':reaudit['canonical']['primary_category_count'],'accounted_unique':reaudit['funnel']['accounted_unique_count'],'coverage_work_remains':True,'real_world_completeness_claimed':False},'freeze':{'phase':'4','freeze_ready':passed,'freeze_scope':'discovery coverage and controlled new-place adoption foundation','open_work_carries_forward':True,'open_work_is_non_blocking':True},'safety':safety}
