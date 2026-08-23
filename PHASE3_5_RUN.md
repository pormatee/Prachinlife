# Phase 3.5 — Verification & Controlled Evidence Persistence

Run from repository root after applying the Phase 3.5 ZIP.

The workflow is intentionally two-step: dry-run verification first, then an explicit controlled evidence-only commit. The commit is idempotent and never writes canonical fields or Production JSON.

```bash
python scripts/verify_and_persist_web_evidence_v2.py
python scripts/verify_and_persist_web_evidence_v2.py --commit
python -m unittest tests_v2.test_v2_phase3_5_controlled_evidence_persistence -v
python -m unittest discover -s tests_v2 -p 'test_*.py'
```

Expected first commit: 10 evidence rows (6 supported, 4 verified), zero blocked. A repeated commit must insert 0 and report 10 already present.
