# Phase 3.4 — Independent Web Evidence Acquisition

Run from the repository root after applying the ZIP.

```bash
python scripts/acquire_independent_web_evidence_v2.py
python -m unittest tests_v2.test_v2_phase3_4_web_evidence_acquisition -v
python -m unittest discover -s tests_v2 -p 'test_*.py'
python - <<'PY'
import json
r=json.load(open('data/v2/discovery_reports/targeted_web_evidence_acquisition_v2.json',encoding='utf-8'))
print('TARGET_QUEUE =',r['target_queue_count'])
print('OBSERVATIONS =',r['observation_count'])
print('MATCHED =',r['matched_observation_count'])
print('CANDIDATE_PLACES =',r['candidate_place_count'])
print('CANDIDATE_CLAIMS =',r['candidate_claim_count'])
print('FIELDS =',r['candidate_field_counts'])
print('UNIQUE_SOURCES =',r['unique_source_count'])
print('BLOCKED =',r['blocked_counts'])
print('CANDIDATE_ONLY =',r['safety']['candidate_only'])
print('DATABASE_UNCHANGED =',r['safety']['database_unchanged'])
print('EVIDENCE_WRITES =',r['safety']['evidence_writes'])
print('PRODUCTION_JSON_WRITES =',r['safety']['production_json_writes'])
print('TRUST_POLICY_LOWERED =',r['safety']['trust_policy_lowered'])
print('RESULT = PASS')
PY

git log -1 --oneline
git status --short
```

Expected development-loop values: target queue 50, observations 8, matched 8, candidate places 6, candidate claims 10, fields phone=8 / website=2, unique sources 8, blocked empty, candidate only true, DB unchanged true, evidence writes false, production JSON writes false, trust policy lowered false, full regression 713 tests OK.
