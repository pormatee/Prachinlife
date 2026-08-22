# Phase 3.1 — Production Place Quality Audit checkpoint

Run from `~/Proprachin` after extracting the ZIP over the repository.

```bash
cd ~/Proprachin

echo "===== PHASE 3.1 AUDIT ====="
python scripts/audit_production_place_quality_v2.py

echo
echo "===== PHASE 3.1 TESTS ====="
python -m unittest tests_v2.test_v2_phase3_1_production_quality -v

echo
echo "===== FULL REGRESSION ====="
python -m unittest discover -s tests_v2 -p 'test_*.py'

echo
echo "===== REPORT CHECK ====="
python - <<'PY'
import json
p='data/v2/discovery_reports/production_place_quality_v2.json'
r=json.load(open(p,encoding='utf-8'))
print('VISIBLE_PLACES =',r['visible_place_count'])
print('QUALITY =',r['quality_tiers'])
print('ACTION_READY =',r['action_ready'])
print('MISSING =',r['missing_fields'])
print('DATASETS =',r['datasets'])
print('TOP_PRIORITY_COUNT =',len(r['top_enrichment_priorities']))
print('RESULT = PASS')
PY

echo
echo "===== HEAD ====="
git log -1 --oneline

echo
echo "===== STATUS ====="
git status --short
```

Expected checkpoint:
- HEAD remains `728fea6` before commit.
- `VISIBLE_PLACES = 333` on the supplied Production snapshot.
- Eat visible places = 55, not 0.
- Additional information ready = 30.
- Phase 3.1 tests = 7/7 OK.
- Full regression = 692/692 OK.
