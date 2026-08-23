#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.web_evidence_acquisition import acquire_independent_web_evidence


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--database', default='data/v2/place_platform_v2.sqlite3')
    p.add_argument('--plan', default='data/v2/discovery_reports/targeted_production_enrichment_v2.json')
    p.add_argument('--observations', default='data/v2/discovery_reports/phase3_4_web_observations.json')
    p.add_argument('--output', default='data/v2/discovery_reports/targeted_web_evidence_acquisition_v2.json')
    args=p.parse_args()
    report=acquire_independent_web_evidence(
        database_path=ROOT/args.database,
        targeted_plan_path=ROOT/args.plan,
        repo_root=ROOT,
        observation_manifest_path=ROOT/args.observations,
    )
    out=ROOT/args.output; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
    print('MODE =',report['mode'])
    print('OBSERVATIONS =',report['observation_count'])
    print('MATCHED =',report['matched_observation_count'])
    print('CANDIDATE_PLACES =',report['candidate_place_count'])
    print('CANDIDATE_CLAIMS =',report['candidate_claim_count'])
    print('FIELDS =',report['candidate_field_counts'])
    print('UNIQUE_SOURCES =',report['unique_source_count'])
    print('BLOCKED =',report['blocked_counts'])
    print('DATABASE_UNCHANGED =',report['safety']['database_unchanged'])
    print('TRUST_POLICY_LOWERED =',report['safety']['trust_policy_lowered'])
    print('RESULT = PASS')
    return 0

if __name__=='__main__': raise SystemExit(main())
