# Development Packet #10 — SQLite Reference Persistence Store

## Goal
Provide a real, stdlib-only persistence implementation for the V2 repository
contracts without coupling the domain model or production UI to SQLite.

## Constraints
- Frozen V1 remains untouched.
- No production integration or behavior change.
- No new third-party dependency.
- Canonical/evidence/revision storage stays separate from consumer publication.
- Evidence and revision identity remain append-oriented.
- Canonical adoption must commit canonical state + revision atomically.
- Near Me semantics must remain compatible with the existing repository contract.
- PostgreSQL/PostGIS migration must remain possible behind the same contracts.

## Tests
- Full V2 regression suite must pass.
- Canonical place survives SQLite round-trip and file reopen.
- Evidence preserves provenance and typed values.
- Unknown-place and duplicate evidence are rejected.
- Adoption persists place + revision atomically; duplicate revision rolls back place update.
- SQLite Near Me respects distance/category/lifecycle behavior.
- Published views persist independently, support Near Me/text search, upsert and unpublish.
- No PostgreSQL/ORM dependency is introduced.

## Non-goals
- PostgreSQL/PostGIS implementation.
- Production migration from V1 JSON.
- Live OSM/Web ingestion.
- Search API/HTTP endpoints.
- Recommendation or ranking beyond current deterministic search contracts.

## Checkpoint
Packet is complete when all V2 tests pass and the diff contains V2-only files.
