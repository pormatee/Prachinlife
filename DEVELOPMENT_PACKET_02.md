# Development Packet #2 — Canonical Place + Evidence + Persistence Boundary

## Goal
Define the storage-neutral canonical Place and field-level Evidence model that will become the shared truth layer for PrachinLife, future local identities, and AI consumers.

## Constraints
- Frozen V1 remains untouched.
- No production UI/JSON integration.
- No database vendor dependency yet.
- One canonical place identity must be reusable by every province/app consumer.
- Manual, automated, official, user, merchant, and future sources use the same evidence boundary.
- Evidence never silently overwrites canonical fields.
- Provenance is retained per evidence record.
- Persistence is accessed through a repository contract.

## Acceptance tests
1. Canonical places have stable UUID identities.
2. Invalid blank place names are rejected.
3. Canonical domain records are immutable values.
4. Evidence records are field-level and source-backed.
5. Adding evidence alone does not mutate canonical data.
6. Orphan evidence is rejected by the reference repository.
7. Multiple independent evidence records can attach to one canonical place.
8. Duplicate evidence IDs are rejected.
9. Repository contract contains no concrete database-driver dependency.
10. Manual sources use the same evidence model as automated sources.
11. All Packet #1 regression tests continue to pass.

## Non-goals
- SQL schema/migrations.
- PostgreSQL/PostGIS selection or deployment.
- Entity resolution/deduplication.
- Confidence aggregation.
- Publication policy implementation.
- Search API.
- Production migration.

## Next checkpoint
Packet #3 should define persistence schema/migrations and database capability tests, including geographic query requirements, while preserving this domain/repository boundary.
