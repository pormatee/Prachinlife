# PrachinLife Phase 2V.1 — Controlled Adoption Dry-run

1. Extract update into `~/Proprachin`.
2. Run full regression.
3. Run the dry-run preview against the current approved review queue.

```bash
cd ~/Proprachin
python -m unittest discover -s tests_v2 -p 'test_*.py'
python scripts/preview_approved_adoption.py
```

Expected safety markers:
- `mode = DRY_RUN`
- `canonical_unchanged = True`
- `draft_unchanged = True`
- `canonical_writes = DISABLED`
- `publication = DISABLED`
- `RESULT = DRY_RUN_PASS`

Phase 2V.1 does not create new canonical places. `create_place_candidate` is explicitly blocked until a later controlled-new-place adoption packet.
