# Development Packet #3 — Persistence Schema + Database Capability Contract

## Goal
Define the storage-neutral persistence contract for the Local Place Intelligence Platform V2, including a canonical schema manifest and deterministic Near Me/geographic query behavior, without selecting or integrating a production database.

## Constraints
- Do not modify frozen V1 code or production behavior.
- Keep V2 domain/discovery code independent of SQLite/PostgreSQL/PostGIS drivers.
- Preserve provenance and append-oriented evidence/history semantics.
- Near Me remains a first-class platform capability.
- No province-specific or category-specific storage workaround.
- No production database connection or migration is introduced in this packet.

## Tests / Acceptance
- All Packet #1 and #2 regression tests remain PASS.
- Schema manifest contains canonical places, evidence, and revisions/history tables.
- Place/source/evidence identity and provenance fields are represented.
- Geographic storage/search capability is explicit.
- Near Me validates radius and coordinates, supports category filtering, excludes closed/inactive by default, and sorts nearest first.
- Repository contract exposes storage-neutral nearby search.
- In-memory reference implementation satisfies the geographic contract deterministically.
- No database-driver dependency is introduced.

## Non-goals
- PostgreSQL/PostGIS deployment.
- SQLite production storage.
- Production migration from V1 JSON.
- Search API or UI integration.
- Recommendation/ranking beyond deterministic distance ordering.

## Rollback
Revert the single Packet #3 commit. Packet #1/#2 remain intact and production V1 is unaffected.
