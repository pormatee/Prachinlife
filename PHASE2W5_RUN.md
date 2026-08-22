# PrachinLife V2 Phase 2W.5 — Canonical Geographic Correction Review

Policy: changing canonical province requires at least two independent source lineages that agree on identity, geographic binding, and proposed province. Dry-run is read-only. Commit is explicit, backed up, atomic, revisioned, audited, and never publishes.

Files:
- `place_platform_v2/geographic_correction.py`
- `place_platform_v2/sqlite_store.py`
- `scripts/review_geographic_correction.py`
- `tests_v2/test_v2_phase2w5_geographic_correction.py`

Run focused tests:

    python -m unittest tests_v2.test_v2_phase2w5_geographic_correction -v

Run full V2 regression:

    python -m unittest discover -s tests_v2 -p 'test_*.py'

Operational CLI accepts `--proposal-json <file>`. Omit `--commit` for dry-run.
