# Development Packet #13 — Controlled V1 → V2 Database Migration

## Goal
Provide an isolated, repeatable migration path from the audited V1 production JSON place records into the SQLite V2 internal database.

## Constraints
- Never mutate V1 JSON inputs.
- Never write to the published read model.
- Entire migration batch is atomic.
- Replaying the same legacy records is idempotent through a durable import ledger.
- Geographic candidate duplicates may share one deterministic canonical place ID.
- Same-name records without coordinates must not be silently merged.
- Every migrated source record retains its own provenance/evidence.
- Frozen V1 production behavior remains unchanged.

## Acceptance tests
- Dry run makes no writes and cannot be committed.
- Commit persists canonical places, field evidence, and migration ledger.
- Reopen preserves migrated state.
- Replay adds no duplicate places/evidence/ledger rows.
- Geo-anchored duplicate across files resolves to one canonical place while preserving two ledger entries.
- Same-name/no-coordinate records remain distinct.
- Exact duplicate categories are unioned.
- Non-place legacy content stays skipped.
- Invalid legacy records block commit.
- A mid-batch constraint failure rolls back the whole transaction.
- Migration never creates a published table/view.
- Source JSON bytes remain unchanged.
- Full V2 regression suite remains green.

## Non-goals
- No production cutover.
- No auto-publication.
- No PostgreSQL/PostGIS deployment.
- No new external discovery source.

## Rollback
Revert this packet commit or delete the isolated V2 migration database. V1 files are untouched.
