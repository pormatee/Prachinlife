# Phase 3.3 — Targeted OSM Evidence Acquisition

Baseline: `0a6509c` — V2 targeted production enrichment queue.

Goal: re-observe exact OSM objects referenced by the Top-50 production enrichment queue and acquire only traceable CANDIDATE phone/website evidence. Never write canonical DB, never write evidence into DB, never modify production JSON, and never lower trust policy.

Run once:

```bash
cd ~/Proprachin

python scripts/acquire_targeted_osm_evidence_v2.py
python -m unittest tests_v2.test_v2_phase3_3_evidence_acquisition -v
python -m unittest discover -s tests_v2 -p 'test_*.py'

python - <<'PY'
import json
p='data/v2/discovery_reports/targeted_osm_evidence_acquisition_v2.json'
r=json.load(open(p, encoding='utf-8'))
print('SOURCE_AVAILABLE =', r.get('source_available'))
print('ACQUISITION_COMPLETE =', r.get('acquisition_complete'))
print('TARGETS =', r['target_count'])
print('MATCHED =', r['matched_target_count'])
print('CANDIDATE_CLAIMS =', r['candidate_claim_count'])
print('FIELDS =', r['candidate_field_counts'])
print('BLOCKED =', r['blocked_counts'])
print('DATABASE_UNCHANGED =', r['safety']['database_unchanged'])
print('EVIDENCE_WRITES =', r['safety']['evidence_writes'])
print('PRODUCTION_JSON_WRITES =', r['safety']['production_json_writes'])
print('TRUST_POLICY_LOWERED =', r['safety']['trust_policy_lowered'])
print('RESULT = PASS' if r.get('source_available') else 'RESULT = SAFE_SOURCE_UNAVAILABLE')
PY

git log -1 --oneline
git status --short
```

Expected safety invariants in both success and source-outage cases:

- `TARGETS = 50`
- `DATABASE_UNCHANGED = True`
- `EVIDENCE_WRITES = False`
- `PRODUCTION_JSON_WRITES = False`
- `TRUST_POLICY_LOWERED = False`
- Full regression: `705 tests OK`

If Overpass is reachable, the report contains only identity/location-matched OSM claims and all emitted claims are `candidate`. If Overpass is unavailable, the run must safe-degrade to `SAFE_SOURCE_UNAVAILABLE` with zero claims and no writes.
