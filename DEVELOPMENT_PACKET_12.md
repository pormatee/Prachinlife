# Development Packet #12 — V1 Production Data Dry-Run Migration Audit

## Goal
Audit real V1 place JSON datasets before any database migration. Produce deterministic, read-only metrics for mapping readiness, invalid records, missing core fields, province/category coverage, and duplicate candidate signals.

## Constraints
- Frozen V1 files are read-only.
- No canonical place creation.
- No database writes.
- No publication changes.
- Use Packet #11 conversion contract; do not create a second mapping implementation.
- Audit failures must be reported, not silently discarded.
- Keep the audit source-neutral and province-neutral.

## Tests
- Existing 138 regression tests remain green.
- Audit does not mutate source JSON.
- Ready/invalid counts are deterministic.
- Missing location/province/category metrics are explicit.
- Province/category coverage is counted.
- Invalid reasons are aggregated.
- Unsupported files are reported safely.
- Candidate-key duplicates can be detected across V1 datasets.
- Auto-discovery is conservative.
- Audit creates no database files.
- Report can be serialized to JSON.

## Non-goals
- No migration commit into SQLite/PostgreSQL.
- No canonical adoption.
- No production cutover.
- No automatic duplicate merge.

## Checkpoint
Packet passes when all V2 tests pass and the production audit CLI can run read-only against the user's repository.
