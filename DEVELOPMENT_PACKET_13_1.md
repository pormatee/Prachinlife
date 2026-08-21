# Development Packet #13.1 — Direct CLI Bootstrap Fix

## Goal
Make the controlled migration CLI executable directly from `scripts/` on Termux or any working directory without requiring PYTHONPATH setup.

## Constraints
- Do not change V1 production data.
- Do not change migration semantics.
- Dry-run remains the default.
- No new dependencies.
- Preserve all prior regressions.

## Change
- Bootstrap repository root into `sys.path` before importing `place_platform_v2`.
- Add an end-to-end regression that executes the CLI directly from an unrelated working directory.

## Acceptance
- Direct `python scripts/migrate_v1_to_v2_sqlite.py --help` succeeds.
- Full V2 regression suite passes.
- No production write occurs.
