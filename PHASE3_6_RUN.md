# Phase 3.6 — Controlled Canonical Adoption Review

Baseline: `aa852ab`.

This phase is read-only. It reviews the Phase 3.5 persisted web evidence against all active evidence for each affected place/field, applies the existing canonical AdoptionPolicy, and emits proposals only. It never applies proposals, changes the DB, or writes Production JSON.

Run:

```bash
python scripts/review_controlled_canonical_adoption_v2.py
python -m unittest tests_v2.test_v2_phase3_6_controlled_canonical_adoption_review -v
python -m unittest discover -s tests_v2 -p 'test_*.py'
```

Expected real review:
- REVIEW_SCOPE_EVIDENCE = 10
- PLACE_FIELDS = 8
- VERIFICATION = {'supported': 6, 'verified': 2}
- ADOPTION = {'proposed': 8}
- DATABASE_UNCHANGED = True
- AUTOMATIC_ADOPTION = False
- full regression = 727 tests OK
