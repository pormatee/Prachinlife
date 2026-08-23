# Phase 3.8 — Controlled Publication Preview / Production Impact Review

Run from repository root after applying the Phase 3.8 ZIP.

```bash
python scripts/preview_controlled_publication_impact_v2.py
python -m unittest tests_v2.test_v2_phase3_8_controlled_publication_impact_preview -v
python -m unittest discover -s tests_v2 -p 'test_*.py'
```

Expected checkpoint on a Phase 3.7 committed database:

- STATUS = PASS
- ADOPTION_REVISIONS = 8
- ADOPTED_PLACES = 6
- MAPPED_PLACES = 6
- CHANGED_RECORDS = 6
- TARGETED_FIELDS = {'phone': 6, 'website': 2}
- IDENTITY_CHANGES = 0
- OVERWRITES = 0
- DESTRUCTIVE_CHANGES = 0
- UNEXPECTED_CHANGES = 0
- BLOCKERS = []
- DATABASE_UNCHANGED = True
- PRODUCTION_JSON_UNCHANGED = True
- PRODUCTION_JSON_WRITES = False
- AUTOMATIC_PUBLICATION = False
- TRUST_POLICY_LOWERED = False

This phase is read-only and must not publish automatically.
